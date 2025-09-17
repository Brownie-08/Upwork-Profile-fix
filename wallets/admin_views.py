from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from decimal import Decimal
from .models import (
    LusitoAccount,
    CommissionTransaction,
    ProjectFund,
    Transaction,
    Wallet,
)
from datetime import timedelta
import json


class SiteAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "total_balance_display",
        "held_funds_display",
        "commission_balance_display",
        "last_updated",
    )

    readonly_fields = (
        "total_balance",
        "held_funds",
        "commission_balance",
        "created_at",
        "updated_at",
        "monthly_commission_chart",
        "transaction_summary",
    )

    fieldsets = (
        (
            "Balance Information",
            {
                "fields": ("total_balance", "held_funds", "commission_balance"),
                "classes": ("wide",),
            },
        ),
        (
            "Statistics",
            {
                "fields": ("monthly_commission_chart", "transaction_summary"),
                "classes": ("wide",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def monthly_commission_chart(self, obj):
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_data = (
            CommissionTransaction.objects.filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        chart_data = [
            (data["month"].strftime("%B %Y"), float(data["total"]))
            for data in monthly_data
        ]
        chart_data_json = json.dumps(chart_data)

        return format_html(
            """
            <div style="margin: 20px 0;">
                <h3>Monthly Commission Trend</h3>
                <div id="chart-container" style="height: 200px;">
                    <script>
                        var chartData = {};
                        renderChart(chartData, "chart-container");
                    </script>
                </div>
            </div>
            """,
            chart_data_json,
        )

    monthly_commission_chart.short_description = "Commission Trends"

    def transaction_summary(self, obj):
        today = timezone.now()
        last_month = today - timedelta(days=30)

        # Get the raw data
        transaction_count = Transaction.objects.filter(
            created_at__gte=last_month
        ).count()
        total_volume = Transaction.objects.filter(created_at__gte=last_month).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        active_holds = ProjectFund.objects.filter(status="HELD").count()
        commission_earned = CommissionTransaction.objects.filter(
            created_at__gte=last_month
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Format the numeric values as strings before passing to format_html
        formatted_volume = "{:,.2f}".format(float(total_volume))
        formatted_commission = "{:,.2f}".format(float(commission_earned))

        return format_html(
            """
            <div style="margin: 20px 0;">
                <h3>30-Day Summary</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">
                            <strong>Transactions</strong><br>{0}
                        </td>
                        <td style="padding: 10px; border: 1px solid #ddd;">
                            <strong>Volume</strong><br>E {1}
                        </td>
                        <td style="padding: 10px; border: 1px solid #ddd;">
                            <strong>Active Holds</strong><br>{2}
                        </td>
                        <td style="padding: 10px; border: 1px solid #ddd;">
                            <strong>Commission Earned</strong><br>E {3}
                        </td>
                    </tr>
                </table>
            </div>
            """,
            transaction_count,
            formatted_volume,
            active_holds,
            formatted_commission,
        )

    transaction_summary.short_description = "Transaction Summary"

    def total_balance_display(self, obj):
        # Convert to float and format as string before passing to format_html
        total_balance = "{:,.2f}".format(float(obj.total_balance))
        return format_html(
            '<div style="font-size: 1.1em;">'
            '<span style="color: green; font-weight: bold;">E {}</span>'
            "</div>",
            total_balance,
        )

    total_balance_display.short_description = "Total Balance"

    def held_funds_display(self, obj):
        # Convert to float and format as string before passing to format_html
        held_funds = "{:,.2f}".format(float(obj.held_funds))
        return format_html(
            '<div style="font-size: 1.1em;">'
            '<span style="color: orange; font-weight: bold;">E {}</span>'
            "</div>",
            held_funds,
        )

    held_funds_display.short_description = "Held Funds"

    def commission_balance_display(self, obj):
        # Convert to float and format as string before passing to format_html
        commission_balance = "{:,.2f}".format(float(obj.commission_balance))
        return format_html(
            '<div style="font-size: 1.1em;">'
            '<span style="color: blue; font-weight: bold;">E {}</span>'
            "</div>",
            commission_balance,
        )

    commission_balance_display.short_description = "Commission Balance"

    def last_updated(self, obj):
        return format_html(
            '<span title="{}">{}</span>',
            obj.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            obj.updated_at.strftime("%b %d, %Y %H:%M"),
        )

    last_updated.short_description = "Last Updated"

    def has_add_permission(self, request):
        return not LusitoAccount.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {"all": ("admin/css/custom_admin.css",)}
        js = ("admin/js/charts.js",)


class ProjectFundAdmin(admin.ModelAdmin):
    list_display = (
        "reference_id",
        "project_title",
        "client_name",
        "amount_display",
        "status_display",
        "commission_amount_display",
        "held_at",
        "released_at",
    )

    list_filter = (
        "status",
        "held_at",
        "released_at",
        ("project__client", admin.RelatedOnlyFieldListFilter),
    )

    search_fields = ("project__title", "reference_id", "project__client__name")

    readonly_fields = ("reference_id", "held_at", "released_at", "status_history")

    fieldsets = (
        (
            "Project Information",
            {
                "fields": (
                    "project",
                    "reference_id",
                    "amount",
                    "commission_amount",
                    "status",
                )
            },
        ),
        ("Timing Information", {"fields": ("held_at", "released_at")}),
        ("History", {"fields": ("status_history",), "classes": ("collapse",)}),
    )

    def project_title(self, obj):
        return format_html(
            '<a href="{}">{}</a>', f"../project/{obj.project.id}/", obj.project.title
        )

    project_title.short_description = "Project"

    def client_name(self, obj):
        return obj.project.client.name

    client_name.short_description = "Client"

    def amount_display(self, obj):
        return format_html(
            '<span style="font-weight: bold;">E {:,.2f}</span>', obj.amount
        )

    amount_display.short_description = "Amount"

    def status_display(self, obj):
        status_colors = {"HELD": "orange", "RELEASED": "green", "CANCELLED": "red"}
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            status_colors.get(obj.status, "black"),
            obj.get_status_display(),
        )

    status_display.short_description = "Status"

    def commission_amount_display(self, obj):
        if obj.commission_amount:
            return format_html(
                '<span style="color: blue;">E {:,.2f}</span>', obj.commission_amount
            )
        return "-"

    commission_amount_display.short_description = "Commission"

    def status_history(self, obj):
        # Assuming you have a related model tracking status changes
        history = obj.statushistory_set.all().order_by("-created_at")
        if not history:
            return "No history available"

        html = ['<table style="width: 100%;">']
        html.append("<tr><th>Date</th><th>Status</th><th>Note</th></tr>")
        for entry in history:
            html.append(
                f"<tr><td>{entry.created_at}</td>"
                f"<td>{entry.status}</td>"
                f"<td>{entry.note}</td></tr>"
            )
        html.append("</table>")
        return format_html("".join(html))

    status_history.short_description = "Status History"


class CommissionTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference_id",
        "project_title",
        "amount_display",
        "rate_display",
        "created_at_display",
    )

    list_filter = (
        "created_at",
        "rate",
        ("project__client", admin.RelatedOnlyFieldListFilter),
    )

    search_fields = (
        "project__title",
        "reference_id",
        "description",
        "project__client__name",
    )

    readonly_fields = ("reference_id", "created_at", "transaction_details")

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("project", "reference_id", "amount", "rate")},
        ),
        (
            "Additional Information",
            {
                "fields": ("description", "created_at", "transaction_details"),
                "classes": ("collapse",),
            },
        ),
    )

    def project_title(self, obj):
        return format_html(
            '<a href="{}">{}</a>', f"../project/{obj.project.id}/", obj.project.title
        )

    project_title.short_description = "Project"

    def amount_display(self, obj):
        return format_html(
            '<span style="font-weight: bold;">E {:,.2f}</span>', obj.amount
        )

    amount_display.short_description = "Amount"

    def rate_display(self, obj):
        return format_html("{}%", obj.rate * 100)

    rate_display.short_description = "Rate"

    def created_at_display(self, obj):
        return obj.created_at.strftime("%b %d, %Y %H:%M")

    created_at_display.short_description = "Created At"

    def transaction_details(self, obj):
        return format_html(
            """
            <div style="margin: 10px 0;">
                <strong>Transaction ID:</strong> {}<br>
                <strong>Created:</strong> {}<br>
                <strong>Project:</strong> {}<br>
                <strong>Client:</strong> {}<br>
                <strong>Amount:</strong> E {:,.2f}<br>
                <strong>Commission Rate:</strong> {}%<br>
                <strong>Status:</strong> {}<br>
                <strong>Description:</strong> {}<br>
            </div>
            """,
            obj.reference_id,
            obj.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            obj.project.title,
            obj.project.client.name,
            obj.amount,
            obj.rate * 100,
            obj.get_status_display(),
            obj.description or "N/A",
        )

    transaction_details.short_description = "Transaction Details"


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = (
        "reference_id",
        "created_at",
        "amount_display",
        "transaction_type",
    )
    fields = (
        "reference_id",
        "transaction_type",
        "amount_display",
        "status",
        "created_at",
    )
    can_delete = False

    def amount_display(self, obj):
        return format_html("E {:,.2f}", obj.amount)

    amount_display.short_description = "Amount"


class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "balance_display",
        "total_transactions",
        "last_transaction",
        "created_at",
    )

    list_filter = ("created_at", "updated_at")

    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )

    readonly_fields = (
        "balance",
        "created_at",
        "updated_at",
        "transaction_summary",
        "wallet_statistics",
    )

    fieldsets = (
        ("Wallet Information", {"fields": ("user", "balance")}),
        (
            "Statistics",
            {
                "fields": ("transaction_summary", "wallet_statistics"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [TransactionInline]

    def balance_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">E {}</span>',
            "{:,.2f}".format(Decimal(obj.balance)),
        )

    balance_display.short_description = "Balance"

    def total_transactions(self, obj):
        return obj.transactions.count()

    total_transactions.short_description = "Total Transactions"

    def last_transaction(self, obj):
        last_tx = obj.transactions.order_by("-created_at").first()
        if last_tx:
            return format_html(
                '<span title="{}">E {:,.2f} ({})</span>',
                last_tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                last_tx.amount,
            )
        return "-"

    last_transaction.short_description = "Last Transaction"

    def transaction_summary(self, obj):
        # Get transaction statistics
        today = timezone.now()
        thirty_days_ago = today - timedelta(days=30)

        by_type = (
            obj.transactions.filter(created_at__gte=thirty_days_ago)
            .values("transaction_type")
            .annotate(total=Sum("amount"), count=Count("id"))
        )

        # Format the summary rows manually
        rows = [
            "<tr>"
            f'<td>{type_stat["transaction_type"]}</td>'
            f'<td>{type_stat["count"]}</td>'
            f'<td>E {type_stat["total"]:.2f}</td>'
            "</tr>"
            for type_stat in by_type
        ]

        html = (
            '<div style="margin: 10px 0;">'
            "<h3>30-Day Transaction Summary</h3>"
            '<table style="width: 100%; border-collapse: collapse;">'
            "<tr><th>Type</th><th>Count</th><th>Total</th></tr>"
            + "".join(rows)
            + "</table></div>"
        )

        return format_html(html)

    transaction_summary.short_description = "Transaction Summary"

    def wallet_statistics(self, obj):
        # Calculate statistics
        total_incoming = (
            obj.transaction_set.filter(type="CREDIT").aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )
        total_outgoing = (
            obj.transaction_set.filter(type="DEBIT").aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )
        largest_transaction = obj.transaction_set.order_by("-amount").first()
        largest_transaction_amount = (
            largest_transaction.amount if largest_transaction else 0
        )

        # Pre-format numbers
        formatted_incoming = f"E {total_incoming:,.2f}"
        formatted_outgoing = f"E {total_outgoing:,.2f}"
        formatted_largest = f"E {largest_transaction_amount:,.2f}"

        html = (
            '<div style="margin: 10px 0;">'
            "<h3>Wallet Statistics</h3>"
            '<table style="width: 100%; border-collapse: collapse;">'
            "<tr>"
            f'<td style="padding: 8px; border: 1px solid #ddd;">'
            f'<strong>Total Incoming</strong><br><span style="color: green;">{formatted_incoming}</span>'
            "</td>"
            f'<td style="padding: 8px; border: 1px solid #ddd;">'
            f'<strong>Total Outgoing</strong><br><span style="color: red;">{formatted_outgoing}</span>'
            "</td>"
            "</tr>"
            "<tr>"
            f'<td style="padding: 8px; border: 1px solid #ddd;">'
            f"<strong>Largest Transaction</strong><br>{formatted_largest}"
            "</td>"
            "</tr>"
            "</table>"
            "</div>"
        )

        return format_html(html)

    wallet_statistics.short_description = "Wallet Statistics"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@staff_member_required
def financial_overview(request):
    # Get date range from request or default to last 30 days
    end_date = timezone.now()
    start_date_param = request.GET.get("start_date")
    end_date_param = request.GET.get("end_date")

    if start_date_param and end_date_param:
        try:
            start_date = timezone.datetime.strptime(start_date_param, "%Y-%m-%d").date()
            end_date = timezone.datetime.strptime(end_date_param, "%Y-%m-%d").date()
        except ValueError:
            start_date = end_date - timedelta(days=30)  # Fallback if parsing fails
    else:
        start_date = end_date - timedelta(days=30)

    # Get site account information
    site_account = LusitoAccount.objects.first()

    # Calculate key metrics
    metrics = {
        "total_commissions": CommissionTransaction.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00"),
        "active_holds": ProjectFund.objects.filter(status="HELD").aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00"),
        "total_transactions": Transaction.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).count(),
        "transaction_volume": Transaction.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00"),
        "new_wallets": Wallet.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).count(),
    }

    # Get daily transaction volumes
    daily_volumes = (
        Transaction.objects.filter(created_at__date__range=[start_date, end_date])
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("day")
    )

    # Get commission distribution
    commission_by_type = (
        CommissionTransaction.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        .values("type")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )

    context = {
        "title": "Financial Overview",
        "site_account": site_account,
        "metrics": metrics,
        "daily_volumes": daily_volumes,
        "commission_by_type": commission_by_type,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }

    return render(request, "admin/financial_overview.html", context)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "transaction_type", "amount", "status", "description")
    search_fields = ("wallet__user__username", "transaction_type", "status")
    list_filter = ("transaction_type", "status")


# Register the admin classes
admin.site.register(LusitoAccount, SiteAccountAdmin)
admin.site.register(ProjectFund, ProjectFundAdmin)
admin.site.register(CommissionTransaction, CommissionTransactionAdmin)
admin.site.register(Wallet, WalletAdmin)
