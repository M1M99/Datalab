import os
from itertools import zip_longest

from django.db.models import Count, Sum, Avg, ExpressionWrapper, F, DecimalField
from django.shortcuts import render

from . import utils
from .forms import UploadForm, ProductImageFormSet
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


def download_template(request):
    return utils.download_template()
