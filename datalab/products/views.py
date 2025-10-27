import os

import pandas as pd
from django.db.models.functions import ExtractQuarter, TruncMonth
from django.http import FileResponse
from itertools import zip_longest


from django.db.models import Count, Sum, Avg, ExpressionWrapper, F, DecimalField
from django.shortcuts import render

from . import utils
from .forms import UploadForm, ProductImageFormSet, DateFilterForm
from .models import Product

from django.conf import settings


def dashboard(request):
    kpi = Product.objects.aggregate(
        products=Count('id'),
        total_qty=Sum('quantity'),
        avg_price=Avg('price')
    )

    revenue_expr = ExpressionWrapper(F("price") * F("quantity"),
                                     output_field=DecimalField(max_digits=14, decimal_places=2))

    top_cats = (Product.objects.values("category")
    .annotate(revenue=Sum(revenue_expr), items=Count("id"))
    .order_by("-revenue")[:5])

    return render(request, "products/dashboard.html", {"kpi": kpi, "top_cats": top_cats})


def product_upload(request):
    ctx = {"form": UploadForm()}

    if request.method == "POST":
        files = request.FILES.getlist("files")
        sheets = request.POST.getlist("sheet_names")
        total_rows = 0
        processed_files = 0

        updir = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(updir, exist_ok=True)

        for i, f in enumerate(files):
            if not f:
                continue

            sheet_name = sheets[i] if i < len(sheets) and sheets[i].strip() else None

            fpath = os.path.join(updir, f.name)

            try:
                with open(fpath, "wb+") as dest:
                    for chunk in f.chunks():
                        dest.write(chunk)

                df = utils.read_any(fpath, sheet_name)
                df = utils.normalize_for_product(df)

                rows = df.to_dict("records")
                total_rows += len(rows)
                processed_files += 1

                for r in rows:
                    Product.objects.update_or_create(
                        sku=r["sku"],
                        defaults=dict(
                            name=r["name"],
                            price=r["price"],
                            quantity=int(r["quantity"]),
                            category=r["category"] or "",
                            tx_date=r["tx_date"],
                        )
                    )

            except Exception as e:
                ctx["error"] = f"Error processing {f.name}: {str(e)}"
                return render(request, "products/upload.html", ctx)

        ctx["msg"] = f"{processed_files} has uploaded successfully, total {total_rows} row changed."

    return render(request, "products/upload.html", ctx)


def product_list(request):
    form = DateFilterForm(request.GET or None)
    qs = Product.objects.all().order_by('-tx_date', '-id')

    if form.is_valid():
        df = form.cleaned_data.get("date_form")
        dt = form.cleaned_data.get("date_to")
        cat = form.cleaned_data.get("category")
        if df:
            qs = qs.filter(tx_date__gte=df)
        if dt:
            qs = qs.filter(tx_date__lte=dt)
        if cat:
            qs = qs.filter(category__icontains=cat)

    return render(request, "products/product_list.html", {"form": form, "qs": qs})


def product_export(request):
    qs = Product.objects.all().order_by('-tx_date', 'sku')
    data = qs.values(
        "sku",
        "name",
        "price",
        "quantity",
        'category', 'tx_date', )
    df = pd.DataFrame.from_records(data)
    path = utils.df_to_excel_response(df,'product_export.xlsx')
    return FileResponse(open(path, 'rb'),as_attachment=True,filename=os.path.basename(path))

def stats_view(request):
    revenue_expr = ExpressionWrapper(F("price") * F("quantity"),
                                     output_field=DecimalField(max_digits=14, decimal_places=2))

    monthly = (Product.objects
               .annotate(month=TruncMonth("tx_date"))
               .values("month")
               .annotate(revenue=Sum(revenue_expr), items=Count("id"))
               )

    quarterly = (Product.objects
                 .annotate(q=ExtractQuarter("tx_date"))
                 .values("q")
                 .annotate(revenue=Sum(revenue_expr), avg_price=Avg("price"))
                 .order_by("q"))

    by_cat = (Product.objects
              .values("category")
              .annotate(mean_price=Avg("price"), total_qty=Sum("quantity"))
              .order_by("-total_qty"))

    top_sku = (Product.objects
    .values("sku", "name", "category")
    .annotate(revenue=Sum(revenue_expr), qty=Sum("quantity"))
    .order_by("-revenue")[:10])

    low_stock = Product.objects.filter(quantity__lte=5).order_by("quantity", "name")[:10]

    ctx = {
        'monthly': list(monthly.values('month', 'revenue', 'items')),
        'quarterly': list(quarterly.values('q', 'revenue', 'avg_price')),
        'by_cat': list(by_cat.values('category', 'mean_price', 'total_qty')),
        'top_sku': list(top_sku.values('sku', 'name', 'category', 'revenue', 'qty')),
        'low_stock': list(low_stock.values('sku', 'name', 'quantity')),
    }

    return render(request, "products/products_stats.html", ctx)

def download_template(request):
    return utils.download_template()
