def isIterable (value):
   try:
      iter(value)
      return True
   except:
      return False