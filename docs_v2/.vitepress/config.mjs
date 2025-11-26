import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Trinity Core",
  description: "AI-powered portfolio generator with self-healing layouts",
  
  // Ignore dead links during development
  ignoreDeadLinks: true,
  
  // Theme configuration
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    
    logo: '/logo.svg',
    
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Architecture', link: '/1_Architecture/1.0_Neural_Symbolic' },
      { text: 'Development', link: '/2_Development/2.0_Setup' },
      { text: 'Features', link: '/3_Features/3.0_Self_Healing' },
      { text: 'GitHub', link: 'https://github.com/fabriziosalmi/trinity' }
    ],

    sidebar: [
      {
        text: '🏗️ Architecture',
        collapsed: false,
        items: [
          { 
            text: 'Neural-Symbolic System', 
            link: '/1_Architecture/1.0_Neural_Symbolic' 
          },
          { 
            text: 'Async & MLOps', 
            link: '/1_Architecture/1.1_Async_MLOps' 
          }
        ]
      },
      {
        text: '🛠️ Development',
        collapsed: false,
        items: [
          { 
            text: 'Setup & Installation', 
            link: '/2_Development/2.0_Setup' 
          },
          { 
            text: 'Code Quality & Security', 
            link: '/2_Development/2.1_Code_Quality' 
          }
        ]
      },
      {
        text: '✨ Features',
        collapsed: false,
        items: [
          { 
            text: 'Self-Healing Layouts', 
            link: '/3_Features/3.0_Self_Healing' 
          },
          { 
            text: 'Centuria Theme Factory', 
            link: '/3_Features/3.1_Centuria_Factory' 
          }
        ]
      },
      {
        text: '🤖 LLM & Caching',
        collapsed: false,
        items: [
          { 
            text: 'LLM Response Caching', 
            link: '/4_LLM_Agents/4.0_LLM_Caching' 
          }
        ]
      },
      {
        text: '📚 Reference',
        collapsed: true,
        items: [
          { text: 'CHANGELOG', link: '/CHANGELOG' },
          { text: 'Contributing', link: '/CONTRIBUTING' },
          { text: 'Security', link: '/SECURITY' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/fabriziosalmi/trinity' }
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2025 Fabrizio Salmi'
    },

    search: {
      provider: 'local'
    },

    editLink: {
      pattern: 'https://github.com/fabriziosalmi/trinity/edit/main/docs_v2/:path',
      text: 'Edit this page on GitHub'
    },

    lastUpdated: {
      text: 'Updated at',
      formatOptions: {
        dateStyle: 'full',
        timeStyle: 'medium'
      }
    }
  },

  // Markdown configuration
  markdown: {
    theme: 'material-theme-palenight',
    lineNumbers: true
  },

  // Build configuration
  outDir: '.vitepress/dist',
  cacheDir: '.vitepress/cache',

  // Head tags
  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }],
    ['meta', { name: 'theme-color', content: '#3eaf7c' }],
    ['meta', { name: 'og:type', content: 'website' }],
    ['meta', { name: 'og:locale', content: 'en' }],
    ['meta', { name: 'og:site_name', content: 'Trinity Core Documentation' }],
    ['meta', { name: 'og:image', content: 'https://trinity-core.org/og-image.png' }]
  ]
})
