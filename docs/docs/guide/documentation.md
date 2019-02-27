# Documentation

## Overview

All documents are created in **Markdown** format and published using **VuePress**.

Documentation is layed out in the following directory structure:
::: vue
docs
├── dist
├── docs
│   ├── `.vuepress`
│   │   ├── `public`
│   │   ├── `styles`
│   │   │   ├── index.styl
│   │   │   └── palette.styl
│   │   └── `config.js`
│   ├── `design`
│   │   └── README.md
│   ├── `guide`
│   │   └── README.md
│   └── README.md
│ 
└── package.json
:::

::: warning Note
Please note the capitalization of the directory name.
:::

- `docs/dist`: holds the static site once built
- `docs/docs`: holds all of the documentation
- `docs/docs/.vuepress`: It is used to store global configuration, components, static resources, etc.
- `docs/docs/.vuepress/public`: Static resource directory. eg. the images that get displayed
- `docs/docs/.vuepress/styles`: Stores style related files.
- `docs/docs/.vuepress/styles/index.styl`: Automatically applied global style files, generated at the ending of the CSS file, have a higher priority than the default style.
- `docs/docs/.vuepress/styles/palette.styl`: The palette is used to override the default color constants and to set the color constants of Stylus.
- `docs/docs/.vuepress/config.js`: Configuration used by vuepress to publish this site.
- `docs/package.json`: the components, dependencies and scripts to manage and build this site.

## Writing Docs

All docs are written in **Markdown**, you can reference the [Markdown guide](https://www.markdownguide.org/) if you are unfamiliar with markdown format.

Every directory needs to have a README.md, which is the top level document, subsequent documents should have a descriptive name using hyphens `(-)` to separate words.

## Live Viewing Docs

To live view the documentation while you edit the markdown, you'll need to install vuepress.

Install vuepress and go to the top docs directory and install the rest of the required packages.

```bash
# install globally
npm install -g vuepress

cd lear/docs

npm install
```

`package.json` has several helper scripts.

```json
{
  "scripts": {
    "docs:dev": "vuepress dev docs --temp .temp",
    "docs:build": "vuepress build docs --temp .temp",
    "docs:show-help": "vuepress --help"
  }
}
```

To live view the documentation, run the following command and open a browser to the host:port it displays:

```bash
npm run docs:dev
```
