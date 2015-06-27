from django.apps import AppConfig


class FilesConfig(AppConfig):
    name = 'files'

    def ready(self):
        Product = self.get_model('')
        watson.register(Product.objects.exclude(productimage=None))
