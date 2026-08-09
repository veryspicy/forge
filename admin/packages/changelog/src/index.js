import { Presets, SingleBar } from "cli-progress";
import process from "node:process";
import { readFile, writeFile } from "node:fs/promises";
import dayjs from "dayjs";
import { ofetch } from "ofetch";
import semver from "semver";
import { existsSync } from "node:fs";
import { convert } from "convert-gitmoji";

async function execCommand(cmd, args, options) {
  const { execa } = await import("execa");
  return ((await execa(cmd, args, options))?.stdout)?.trim() || "";
}
function notNullish(v) {
  return v !== null && v !== void 0;
}
function partition(array, ...filters) {
  const result = Array.from({ length: filters.length + 1 }).fill(null).map(() => []);
  array.forEach((e, idx, arr) => {
    let i = 0;
    for (const filter of filters) {
      if (filter(e, idx, arr)) {
        result[i].push(e);
        return;
      }
      i += 1;
    }
    result[i].push(e);
  });
  return result;
}
function groupBy(items, key, groups = {}) {
  for (const item of items) {
    const v = item[key];
    groups[v] ||= [];
    groups[v].push(item);
  }
  return groups;
}
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
function join(array, glue = ", ", finalGlue = " and ") {
  if (!array || array.length === 0) return "";
  if (array.length === 1) return array[0];
  if (array.length === 2) return array.join(finalGlue);
  return `${array.slice(0, -1).join(glue)}${finalGlue}${array.slice(-1)}`;
}

const VERSION_REG = /^v\d+\.\d+\.\d+(-(beta|alpha)\.\d+)?/;
const VERSION_REG_OF_MARKDOWN = /## \[v\d+\.\d+\.\d+(-(beta|alpha)\.\d+)?]/g;
const VERSION_WITH_RELEASE = /release\sv\d+\.\d+\.\d+(-(beta|alpha)\.\d+)?/;

/** Get the total git tags */
async function getTotalGitTags() {
  const filtered = (await execCommand("git", [
    "--no-pager",
    "tag",
    "-l",
    "--sort=v:refname"
  ])).split("\n").filter((tag) => VERSION_REG.test(tag));
  return semver.sort(filtered);
}
/** Get map of the git tag and date */
async function getTagDateMap() {
  const tagDateStr = await execCommand("git", [
    "--no-pager",
    "log",
    "--tags",
    "--simplify-by-decoration",
    "--pretty=format:%ci %d"
  ]);
  const TAG_MARK = "tag: ";
  const map = /* @__PURE__ */ new Map();
  tagDateStr.split("\n").filter((item) => item.includes(TAG_MARK)).forEach((item) => {
    const [dateStr, tagStr] = item.split(TAG_MARK);
    const date = dayjs(dateStr).format("YYYY-MM-DD");
    const tag = tagStr.match(VERSION_REG)?.[0];
    if (tag && date) map.set(tag.trim(), date);
  });
  return map;
}
function getFromToTags(tags) {
  const result = [];
  if (tags.length < 2) return result;
  const releaseTags = tags.filter((tag) => !isPrerelease(tag));
  const reversedTags = [...tags].reverse();
  reversedTags.forEach((tag, index) => {
    if (index < reversedTags.length - 1) {
      const to = tag;
      let from = reversedTags[index + 1];
      if (!isPrerelease(to)) from = releaseTags[releaseTags.indexOf(to) - 1];
      result.push({
        from,
        to
      });
    }
  });
  return result.reverse();
}
async function getGitMainBranchName() {
  return await execCommand("git", [
    "rev-parse",
    "--abbrev-ref",
    "HEAD"
  ]);
}
async function getCurrentGitBranch() {
  const tag = await execCommand("git", [
    "tag",
    "--points-at",
    "HEAD"
  ]);
  const main = getGitMainBranchName();
  return tag || main;
}
async function getGitHubRepo() {
  const url = await execCommand("git", [
    "config",
    "--get",
    "remote.origin.url"
  ]);
  const match = url.match(/github\.com[/:]([\w\d._-]+?)\/([\w\d._-]+?)(\.git)?$/i);
  if (!match) throw new Error(`Can not parse GitHub repo from url ${url}`);
  return `${match[1]}/${match[2]}`;
}
function isPrerelease(version) {
  return !/^[^.]*[\d.]+$/.test(version);
}
function getFirstGitCommit() {
  return execCommand("git", [
    "rev-list",
    "--max-parents=0",
    "HEAD"
  ]);
}
async function getGitDiff(from, to = "HEAD") {
  return (await execCommand("git", [
    "--no-pager",
    "log",
    `${from ? `${from}...` : ""}${to}`,
    "--pretty=\"----%n%s|%h|%an|%ae%n%b\"",
    "--name-status"
  ])).split("----\n").splice(1).map((line) => {
    const [firstLine, ...body] = line.split("\n");
    const [message, shortHash, authorName, authorEmail] = firstLine.split("|");
    return {
      message,
      shortHash,
      author: {
        name: authorName,
        email: authorEmail
      },
      body: body.join("\n")
    };
  });
}
function parseGitCommit(commit) {
  const ConventionalCommitRegex = /(?<type>[a-z]+)(\((?<scope>.+)\))?(?<breaking>!)?: (?<description>.+)/i;
  const CoAuthoredByRegex = /co-authored-by:\s*(?<name>.+)(<(?<email>.+)>)/gim;
  const PullRequestRE = /\([a-z]*(#\d+)\s*\)/gm;
  const IssueRE = /(#\d+)/gm;
  const match = commit.message.match(ConventionalCommitRegex);
  if (!match?.groups) return null;
  const type = match.groups.type;
  const scope = match.groups.scope || "";
  const isBreaking = Boolean(match.groups.breaking);
  let description = match.groups.description;
  const references = [];
  for (const m of description.matchAll(PullRequestRE)) references.push({
    type: "pull-request",
    value: m[1]
  });
  for (const m of description.matchAll(IssueRE)) if (!references.some((i) => i.value === m[1])) references.push({
    type: "issue",
    value: m[1]
  });
  references.push({
    value: commit.shortHash,
    type: "hash"
  });
  description = description.replace(PullRequestRE, "").trim();
  const authors = [commit.author];
  const matches = commit.body.matchAll(CoAuthoredByRegex);
  for (const $match of matches) {
    const { name = "", email = "" } = $match.groups || {};
    const author = {
      name: name.trim(),
      email: email.trim()
    };
    authors.push(author);
  }
  return {
    ...commit,
    authors,
    resolvedAuthors: [],
    description,
    type,
    scope,
    references,
    isBreaking
  };
}
async function getGitCommits(from, to = "HEAD") {
  return (await getGitDiff(from, to)).map((commit) => parseGitCommit(commit)).filter(notNullish);
}
function getHeaders(githubToken) {
  return {
    accept: "application/vnd.github.v3+json",
    authorization: `token ${githubToken}`
  };
}
async function getResolvedAuthorLogin(github, commitHashes, email) {
  const { repo, token } = github;
  let login = "";
  try {
    login = (await ofetch(`https://api.github.com/search/users?q=${encodeURIComponent(email)}`, { headers: getHeaders(token) })).items[0].login;
  } catch {}
  if (login) return login;
  try {
    login = (await ofetch(`https://ungh.cc/users/find/${email}`))?.user?.username || "";
  } catch {}
  if (login) return login;
  if (!token) return login;
  if (commitHashes.length) try {
    login = (await ofetch(`https://api.github.com/repos/${repo}/commits/${commitHashes[0]}`, { headers: getHeaders(token) }))?.author?.login || "";
  } catch {}
  return login;
}
async function getGitCommitsAndResolvedAuthors(commits, github, resolvedLogins) {
  const resultCommits = [];
  const map = /* @__PURE__ */ new Map();
  for await (const commit of commits) {
    const resolvedAuthors = [];
    for await (const [index, author] of commit.authors.entries()) {
      const { email, name } = author;
      if (email && name) {
        const commitHashes = [];
        if (index === 0) commitHashes.push(commit.shortHash);
        const resolvedAuthor = {
          name,
          email,
          commits: commitHashes,
          login: ""
        };
        if (!resolvedLogins?.has(email)) {
          const login = await getResolvedAuthorLogin(github, commitHashes, email);
          resolvedAuthor.login = login;
          resolvedLogins?.set(email, login);
        } else resolvedAuthor.login = resolvedLogins?.get(email) || "";
        resolvedAuthors.push(resolvedAuthor);
        if (!map.has(email)) map.set(email, resolvedAuthor);
      }
    }
    const resultCommit = {
      ...commit,
      resolvedAuthors
    };
    resultCommits.push(resultCommit);
  }
  return {
    commits: resultCommits,
    contributors: Array.from(map.values())
  };
}

function createDefaultOptions() {
  return {
    cwd: process.cwd(),
    types: {
      feat: "🚀 Features",
      fix: "🐞 Bug Fixes",
      perf: "🔥 Performance",
      optimize: "🛠 Optimizations",
      refactor: "💅 Refactors",
      docs: "📖 Documentation",
      build: "📦 Build",
      types: "🌊 Types",
      chore: "🏡 Chore",
      examples: "🏀 Examples",
      test: "✅ Tests",
      style: "🎨 Styles",
      ci: "🤖 CI"
    },
    github: {
      repo: "",
      token: process.env.GITHUB_TOKEN || ""
    },
    from: "",
    to: "",
    tags: [],
    tagDateMap: /* @__PURE__ */ new Map(),
    capitalize: false,
    emoji: true,
    titles: { breakingChanges: "🚨 Breaking Changes" },
    output: "CHANGELOG.md",
    regenerate: false
  };
}
async function getVersionFromPkgJson(cwd) {
  let newVersion = "";
  try {
    const pkgJson = await readFile(`${cwd}/package.json`, "utf-8");
    newVersion = JSON.parse(pkgJson)?.version || "";
  } catch {}
  return { newVersion };
}
async function createOptions(options) {
  const opts = createDefaultOptions();
  Object.assign(opts, options);
  const { newVersion } = await getVersionFromPkgJson(opts.cwd);
  opts.github.repo ||= await getGitHubRepo();
  const tags = await getTotalGitTags();
  opts.tags = tags;
  opts.from ||= tags[tags.length - 1];
  opts.to ||= `v${newVersion}`;
  if (opts.to === opts.from) {
    const lastTag = tags[tags.length - 2];
    const firstCommit = await getFirstGitCommit();
    opts.from = lastTag || firstCommit;
  }
  opts.tagDateMap = await getTagDateMap();
  opts.prerelease ||= isPrerelease(opts.to);
  const isFromPrerelease = isPrerelease(opts.from);
  if (!isPrerelease(newVersion) && isFromPrerelease) {
    const allReleaseTags = opts.tags.filter((tag) => !isPrerelease(tag) && tag !== opts.to);
    opts.from = allReleaseTags[allReleaseTags.length - 1];
  }
  return opts;
}

function formatReferences(references, githubRepo, type) {
  const referencesString = join(references.filter((i) => {
    if (type === "issues") return i.type === "issue" || i.type === "pull-request";
    return i.type === "hash";
  }).map((ref) => {
    if (!githubRepo) return ref.value;
    if (ref.type === "pull-request" || ref.type === "issue") return `https://github.com/${githubRepo}/issues/${ref.value.slice(1)}`;
    return `[<samp>(${ref.value.slice(0, 5)})</samp>](https://github.com/${githubRepo}/commit/${ref.value})`;
  })).trim();
  if (type === "issues") return referencesString && `in ${referencesString}`;
  return referencesString;
}
function formatLine(commit, options) {
  const prRefs = formatReferences(commit.references, options.github.repo, "issues");
  const hashRefs = formatReferences(commit.references, options.github.repo, "hash");
  let authors = join([...new Set(commit.resolvedAuthors.map((i) => i.login ? `@${i.login}` : `**${i.name}**`))]).trim();
  if (authors) authors = `by ${authors}`;
  let refs = [
    authors,
    prRefs,
    hashRefs
  ].filter((i) => i?.trim()).join(" ");
  if (refs) refs = `&nbsp;-&nbsp; ${refs}`;
  return [options.capitalize ? capitalize(commit.description) : commit.description, refs].filter((i) => i?.trim()).join(" ");
}
function formatTitle(name, options) {
  const emojisRE = /([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g;
  let formatName = name.trim();
  if (!options.emoji) formatName = name.replace(emojisRE, "").trim();
  return `### &nbsp;&nbsp;&nbsp;${formatName}`;
}
function formatSection(commits, sectionName, options) {
  if (!commits.length) return [];
  const lines = [
    "",
    formatTitle(sectionName, options),
    ""
  ];
  const scopes = groupBy(commits, "scope");
  let useScopeGroup = true;
  if (!Object.entries(scopes).some(([k, v]) => k && v.length > 1)) useScopeGroup = false;
  Object.keys(scopes).sort().forEach((scope) => {
    let padding = "";
    let prefix = "";
    const scopeText = `**${scope}**`;
    if (scope && useScopeGroup) {
      lines.push(`- ${scopeText}:`);
      padding = "  ";
    } else if (scope) prefix = `${scopeText}: `;
    lines.push(...scopes[scope].reverse().map((commit) => `${padding}- ${prefix}${formatLine(commit, options)}`));
  });
  return lines;
}
function getUserGithub(userName) {
  return `https://github.com/${userName}`;
}
function getGitUserAvatar(userName) {
  return `${getUserGithub(userName)}.png?size=48`;
}
function createContributorLine(contributors) {
  let loginLine = "";
  let unLoginLine = "";
  const contributorMap = /* @__PURE__ */ new Map();
  contributors.forEach((contributor) => {
    contributorMap.set(contributor.email, contributor);
  });
  Array.from(contributorMap.values()).forEach((contributor, index) => {
    const { name, email, login } = contributor;
    if (!login) {
      let line = `[${name}](mailto:${email})`;
      if (index < contributors.length - 1) line += ",&nbsp;";
      unLoginLine += line;
    } else {
      const githubUrl = getUserGithub(login);
      const avatar = getGitUserAvatar(login);
      loginLine += `[![${login}](${avatar})](${githubUrl})&nbsp;&nbsp;`;
    }
  });
  return `${loginLine}\n${unLoginLine}`;
}
async function generateMarkdown(params) {
  const { options, showTitle, contributors } = params;
  const commits = params.commits.filter((commit) => commit.description.match(VERSION_WITH_RELEASE) === null);
  const lines = [];
  let url = `https://github.com/${options.github.repo}/compare/${options.from}...${options.to}`;
  if (!options.from) {
    const mainBranch = await getGitMainBranchName();
    url = `https://github.com/${options.github.repo}/compare/${options.to}...${mainBranch || "HEAD"}`;
  }
  if (showTitle) {
    const date = options.tagDateMap.get(options.to) || dayjs().format("YYYY-MM-DD");
    let title = `## [${options.to}](${url})`;
    if (date) title += ` (${date})`;
    lines.push(title);
  }
  const [breaking, changes] = partition(commits, (c) => c.isBreaking);
  const group = groupBy(changes, "type");
  lines.push(...formatSection(breaking, options.titles.breakingChanges, options));
  for (const type of Object.keys(options.types)) {
    const items = group[type] || [];
    lines.push(...formatSection(items, options.types[type], options));
  }
  if (!lines.length) lines.push("*No significant changes*");
  if (!showTitle) lines.push("", `##### &nbsp;&nbsp;&nbsp;&nbsp;[View changes on GitHub](${url})`);
  if (showTitle) {
    lines.push("", "### &nbsp;&nbsp;&nbsp;❤️ Contributors", "");
    const contributorLine = createContributorLine(contributors);
    lines.push(contributorLine);
  }
  return convert(lines.join("\n").trim(), true);
}
async function isVersionInMarkdown(newVersion, mdPath) {
  let isIn = false;
  let md = "";
  try {
    md = await readFile(mdPath, "utf8");
  } catch {}
  if (md) {
    const matches = md.match(VERSION_REG_OF_MARKDOWN);
    if (matches?.length) {
      const versionInMarkdown = `## [${newVersion}]`;
      isIn = matches.includes(versionInMarkdown);
    }
  }
  return isIn;
}
async function writeMarkdown(md, mdPath, regenerate = false) {
  let changelogMD = "";
  const changelogPrefix = "# Changelog";
  if (!existsSync(mdPath)) await writeFile(mdPath, `${changelogPrefix}\n\n`, "utf8");
  if (!regenerate) changelogMD = await readFile(mdPath, "utf8");
  if (!changelogMD.startsWith(changelogPrefix)) changelogMD = `${changelogPrefix}\n\n${changelogMD}`;
  const lastEntry = changelogMD.match(/^###?\s+.*$/m);
  if (lastEntry) changelogMD = `${changelogMD.slice(0, lastEntry.index) + md}\n\n${changelogMD.slice(lastEntry.index)}`;
  else changelogMD += `\n${md}\n\n`;
  await writeFile(mdPath, changelogMD);
}

async function getChangelogMarkdown(options, showTitle = true) {
  const opts = await createOptions(options);
  const current = await getCurrentGitBranch();
  const to = opts.tags.includes(opts.to) ? opts.to : current;
  const gitCommits = await getGitCommits(opts.from, to);
  const resolvedLogins = /* @__PURE__ */ new Map();
  const { commits, contributors } = await getGitCommitsAndResolvedAuthors(gitCommits, opts.github, resolvedLogins);
  return {
    markdown: await generateMarkdown({
      commits,
      options: opts,
      showTitle,
      contributors
    }),
    commits,
    options: opts
  };
}
async function getTotalChangelogMarkdown(options, showProgress = true) {
  const opts = await createOptions(options);
  let bar = null;
  if (showProgress) bar = new SingleBar({ format: "generate total changelog: [{bar}] {percentage}% | ETA: {eta}s | {value}/{total}" }, Presets.shades_classic);
  const tags = getFromToTags(opts.tags);
  if (tags.length === 0) {
    const { markdown } = await getChangelogMarkdown(opts);
    return markdown;
  }
  bar?.start(tags.length, 0);
  let markdown = "";
  const resolvedLogins = /* @__PURE__ */ new Map();
  for await (const [index, tag] of tags.entries()) {
    const { from, to } = tag;
    const { commits, contributors } = await getGitCommitsAndResolvedAuthors(await getGitCommits(from, to), opts.github, resolvedLogins);
    markdown = `${await generateMarkdown({
      commits,
      options: {
        ...opts,
        from,
        to
      },
      showTitle: true,
      contributors
    })}\n\n${markdown}`;
    bar?.update(index + 1);
  }
  bar?.stop();
  return markdown;
}
async function generateChangelog(options) {
  const opts = await createOptions(options);
  const existContent = await isVersionInMarkdown(opts.to, opts.output);
  if (!opts.regenerate && existContent) return;
  const { markdown } = await getChangelogMarkdown(opts);
  await writeMarkdown(markdown, opts.output, opts.regenerate);
}
async function generateTotalChangelog(options, showProgress = true) {
  const opts = await createOptions(options);
  await writeMarkdown(await getTotalChangelogMarkdown(opts, showProgress), opts.output, true);
}

export { generateChangelog, generateTotalChangelog, getChangelogMarkdown, getTotalChangelogMarkdown };
