import configparser

class Config():
  
  _config = None
  
  def __init__(self, ini = None):
    if not Config._config:
      Config._config = configparser.ConfigParser()
      Config._config.read(ini)
  
  def get(self, section, key, default = None):
    if default is None:
      return Config._config.get(section, key)
    else:
      return Config._config.get(section, key, fallback = default)
  
  def getint(self, section, key, default = None):
    if default is None:
      return Config._config.getint(section, key)
    else:
      return Config._config.getint(section, key, fallback = default)
      
  
  def items(self, section):
    return Config._config.items(section)
