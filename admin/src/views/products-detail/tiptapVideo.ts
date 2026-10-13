import { Node, mergeAttributes } from '@tiptap/core';

/**
 * 富文本视频节点（TIPTAP-VIDEO-NODE）。
 *
 * 官方 npm 无 @tiptap/extension-video 包（404），为保持与项目 @tiptap/* 3.31.4
 * 完全兼容且不引入第三方依赖，按 tiptap Node.create 规范自建 video 块级原子节点：
 * - 渲染为 <video controls src="..." width="100%">，C 端 v-html 可直接播放
 * - 提供 setVideo({ src }) 命令，与 Image 扩展的 setImage 用法一致
 */

export interface VideoOptions {
  HTMLAttributes: Record<string, any>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    video: {
      setVideo: (options: { src: string }) => ReturnType;
    };
  }
}

export const Video = Node.create<VideoOptions>({
  name: 'video',
  group: 'block',
  atom: true,
  draggable: true,

  addOptions() {
    return {
      HTMLAttributes: {}
    };
  },

  addAttributes() {
    return {
      src: { default: null },
      controls: { default: true },
      width: { default: '100%' },
      autoplay: { default: false }
    };
  },

  parseHTML() {
    return [{ tag: 'video' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['video', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes)];
  },

  addCommands() {
    return {
      setVideo:
        options =>
        ({ commands }) => {
          return commands.insertContent({ type: this.name, attrs: options });
        }
    };
  }
});
