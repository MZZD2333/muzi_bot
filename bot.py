import muzi

muzi.init(config='./config.json')

muzi.load_plugin_dir('plugins')

muzi.run()
