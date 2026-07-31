// Vue template $t 全局类型声明
declare module 'vue' {
  interface ComponentCustomProperties {
    $t: (key: string, ...args: any[]) => string
  }
}

export {}
