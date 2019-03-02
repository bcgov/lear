const container = require("markdown-it-container");

module.exports = ctx => ({
  dest: "dist/docs",
  base: "/lear/",
  locales: {
    "/": {
      lang: "en-US",
      title: "LEAR Documentation",
      description:
        "Legal Entities and Asset Registry architectural and technical documentation"
    }
  },
  head: [
    ["link", { rel: "icon", href: `/logo.png` }],
    ["link", { rel: "manifest", href: "/manifest.json" }],
    ["meta", { name: "theme-color", content: "#3eaf7c" }],
    ["meta", { name: "apple-mobile-web-app-capable", content: "yes" }],
    [
      "meta",
      { name: "apple-mobile-web-app-status-bar-style", content: "black" }
    ],
    [
      "link",
      { rel: "apple-touch-icon", href: `/icons/apple-touch-icon-152x152.png` }
    ],
    [
      "link",
      {
        rel: "mask-icon",
        href: "/icons/safari-pinned-tab.svg",
        color: "#3eaf7c"
      }
    ],
    [
      "meta",
      {
        name: "msapplication-TileImage",
        content: "/icons/msapplication-icon-144x144.png"
      }
    ],
    ["meta", { name: "msapplication-TileColor", content: "#000000" }]
  ],
  theme: "@vuepress/vue",
  themeConfig: {
    repo: "bcgov/lear",
    editLinks: true,
    docsDir: "docs/docs",
    locales: {
      "/": {
        label: "English",
        selectText: "Languages",
        editLinkText: "Edit this page on GitHub",
        lastUpdated: "Last Updated",
        nav: require("./nav/en"),
        sidebar: {
          "/guide/": getGuideSidebar(
            "Guide",
            "Web App",
            "API Services",
            "Databases",
            "Testing"
          ),
          "/design/": getDesignSidebar(
            "Wardley Map",
            "Introduction",
            "MVP1 - Annual Report"
          )
        }
      }
    }
  },
  plugins: [
    ["@vuepress/i18n-ui", !ctx.isProd],
    ["@vuepress/back-to-top", true],
    [
      "@vuepress/pwa",
      {
        serviceWorker: true,
        updatePopup: true
      }
    ],
    ["@vuepress/medium-zoom", true],
    ["@vuepress/notification", true],
    [
      "@vuepress/google-analytics",
      {
        ga: "UA-135203050-1"
      }
    ]
  ],
  extendMarkdown(md) {
    md.use(container, "upgrade", {
      render: (tokens, idx) =>
        tokens[idx].nesting === 1
          ? `<UpgradePath title="${tokens[idx].info
              .trim()
              .slice("upgrade".length)
              .trim()}">`
          : "</UpgradePath>"
    });
  }
});

function getGuideSidebar(groupA, groupB, groupC, groupD, groupE) {
  return [
    {
      title: groupA,
      collapsable: false,
      children: ["", "getting-started", "standards", "tools", "documentation"]
    },
    {
      title: groupB,
      collapsable: false,
      children: [
        "web-app/setup",
        "web-app/directory-structure",
        "web-app/i18n",
        "web-app/deploy"
      ]
    },
    {
      title: groupC,
      collapsable: false,
      children: [
        "api-services/setup",
        "api-services/directory-structure",
        "api-services/deploy"
      ]
    },
    {
      title: groupD,
      collapsable: false,
      children: ["database/"]
    },
    {
      title: groupE,
      collapsable: false,
      children: [
        "testing/quality-plan",
        "testing/annual-report-test-plan"
        ]
    }
  ];
}

function getDesignSidebar(designTitle, pluginIntro, designMvp) {
  return [
    {
      title: designTitle,
      collapsable: false,
      children: ["", "methodology"]
    },
    {
      title: designMvp,
      collapsable: false,
      children: ["mvp-ar/", "mvp-ar/database"]
    }
  ];
}
