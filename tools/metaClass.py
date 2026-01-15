# tools/metaClass.py
class Meta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        cls.instances = {}  # 类级别实例字典

    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        # 提取 name：优先从 kwargs，其次从 args 的第一个位置参数
        name = kwargs.get('name')
        if name is None and len(args) >= 1:
            # 假设 __init__ 的第一个参数是 name
            name = args[0]
        if name is not None:
            cls.instances[name] = instance
        return instance