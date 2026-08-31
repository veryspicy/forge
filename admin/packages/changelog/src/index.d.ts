interface GitCommitAuthor {
  name: string;
  email: string;
}
interface RawGitCommit {
  message: string;
  body: string;
  shortHash: string;
  author: GitCommitAuthor;
}
interface Reference {
  type: 'hash' | 'issue' | 'pull-request';
  value: string;
}
interface ResolvedAuthor extends GitCommitAuthor {
  commits: string[];
  login: string;
}
interface GitCommit extends RawGitCommit {
  description: string;
  type: string;
  scope: string;
  references: Reference[];
  authors: GitCommitAuthor[];
  resolvedAuthors: ResolvedAuthor[];
  isBreaking: boolean;
}
interface GithubConfig {
  repo: string;
  token: string;
}
interface ChangelogOption {
  cwd: string;
  types: Record<string, string>;
  github: GithubConfig;
  from: string;
  to: string;
  tags: string[];
  tagDateMap: Map<string, string>;
  capitalize: boolean;
  emoji: boolean;
  titles: { breakingChanges: string };
  output: string;
  regenerate: boolean;
  prerelease?: boolean;
}

declare function getChangelogMarkdown(
  options?: Partial<ChangelogOption>,
  showTitle?: boolean
): Promise<{
  markdown: string;
  commits: GitCommit[];
  options: ChangelogOption;
}>;
declare function getTotalChangelogMarkdown(options?: Partial<ChangelogOption>, showProgress?: boolean): Promise<string>;
declare function generateChangelog(options?: Partial<ChangelogOption>): Promise<void>;
declare function generateTotalChangelog(options?: Partial<ChangelogOption>, showProgress?: boolean): Promise<void>;

export {
  type ChangelogOption,
  generateChangelog,
  generateTotalChangelog,
  getChangelogMarkdown,
  getTotalChangelogMarkdown
};
