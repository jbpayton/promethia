# defines a singelton class DataMapper
# DataMapper keeps a map of strings to values

class VariableMap:
    __instance = None

    @staticmethod
    def get_instance():
        if VariableMap.__instance is None:
            VariableMap()
        return VariableMap.__instance

    def __init__(self):
        if VariableMap.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            print("Creating VariableMap instance")
            VariableMap.__instance = self
            self.data_map = {}

    def set_data(self, key, value):
        print(f"Setting value {key}")
        self.data_map[key] = value

    def get_data(self, key):
        print(f"Getting {key}")
        return self.data_map.get(key, None)


if __name__ == "__main__":
    # Example usage of the VariableMap
    variable = VariableMap.get_instance().get_data("variable")
    print(variable)
    variable = 55
    VariableMap.get_instance().set_data("variable", variable)
    print(VariableMap.get_instance().get_data("variable"))
