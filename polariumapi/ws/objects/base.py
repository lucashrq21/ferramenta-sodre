#=============================================================================#
#                             API BY: Lucas Code                              #    
#                     https://www.youtube.com/@lucascode                      #
#=============================================================================#
class Base(object):
    def __init__(self):
        self.__name = None
        
    @property
    def name(self):
        return self.__name
