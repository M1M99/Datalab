from django.db import models


class Product(models.Model):
    sku=models.CharField(max_length=64,unique=True)
    name=models.CharField(max_length=255)
    category=models.CharField(max_length=120,blank=True,null=True)

    price=models.DecimalField(decimal_places=2,max_digits=12)
    quantity=models.PositiveIntegerField(default=0)

    tx_date=models.DateField()

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def revenue(self):
        return float(self.price) * self.quantity

    def __str__(self):
        return f"{self.sku} - {self.name}"



class ProductImage(models.Model):
    listing = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image=models.ImageField(upload_to='product/extra/photos', blank=True, null=True)
    alt=models.CharField(max_length=200,blank=True)
