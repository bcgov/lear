module.exports = {
  configureWebpack: {
    devtool: 'source-map'
  },
  transpileDependencies: ['vuex-persist', 'vuetify'],
  publicPath: process.env.VUE_APP_PATH
}
