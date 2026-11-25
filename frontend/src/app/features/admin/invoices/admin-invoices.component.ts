import { CurrencyPipe, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  ElementRef,
  OnInit,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  AdminInvoiceSummary,
  AdminInvoicesService,
  DianStepStatus,
} from '../../../core/services/admin-invoices.service';
import { InvoiceDetail, InvoiceService } from '../../../core/services/invoice.service';

interface DianBadgeMeta {
  label: string;
  icon: string;
  toneClass: string;
}

const DIAN_STATUS_META: Record<string, DianBadgeMeta> = {
  APROBADA: { label: 'APROBADA', icon: '✓', toneClass: 'dian--approved' },
  LISTO: { label: 'LISTO', icon: '⚙', toneClass: 'dian--ready' },
  PENDIENTE: { label: 'PENDIENTE', icon: '⏳', toneClass: 'dian--pending' },
  ERROR: { label: 'ERROR', icon: '✕', toneClass: 'dian--error' },
};

@Component({
  selector: 'app-admin-invoices',
  imports: [CurrencyPipe, DatePipe, ReactiveFormsModule, RouterLink],
  templateUrl: './admin-invoices.component.html',
  styleUrls: ['./admin-invoices.component.css'],
})
export class AdminInvoicesComponent implements OnInit {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly adminInvoicesService = inject(AdminInvoicesService);
  private readonly invoiceService = inject(InvoiceService);

  private readonly detailHeading = viewChild<ElementRef<HTMLElement>>('detailHeading');

  readonly filterForm = this.fb.group({
    search: [''],
    estado_respuesta: ['' as '' | DianStepStatus],
  });

  readonly invoices = signal<AdminInvoiceSummary[]>([]);
  readonly totalCount = signal(0);
  readonly currentPage = signal(1);
  readonly pageSize = 8;

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly selectedInvoice = signal<InvoiceDetail | null>(null);
  readonly detailLoading = signal(false);
  readonly detailError = signal<string | null>(null);

  readonly busyAction = signal<{ id: number; kind: 'pdf' | 'xml' | 'email' } | null>(null);
  readonly actionMessage = signal<string | null>(null);
  readonly actionError = signal<string | null>(null);

  readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.totalCount() / this.pageSize))
  );

  readonly pageNumbers = computed(() =>
    Array.from({ length: this.totalPages() }, (_, idx) => idx + 1)
  );

  ngOnInit(): void {
    this.loadInvoices();
  }

  applyFilters(): void {
    this.currentPage.set(1);
    this.loadInvoices();
  }

  clearFilters(): void {
    this.filterForm.reset({
      search: '',
      estado_respuesta: '',
    });
    this.currentPage.set(1);
    this.loadInvoices();
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages() || page === this.currentPage()) return;
    this.currentPage.set(page);
    this.loadInvoices();
  }

  loadInvoices(): void {
    this.loading.set(true);
    this.error.set(null);

    const { search, estado_respuesta } = this.filterForm.getRawValue();
    this.adminInvoicesService
      .getInvoices({
        search,
        estado_respuesta,
        page: this.currentPage(),
      })
      .subscribe({
        next: (res) => {
          this.invoices.set(res.results);
          this.totalCount.set(res.count);
          this.loading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(
            err.error?.detail ?? 'No pudimos cargar el listado de facturas electrónicas.'
          );
          this.loading.set(false);
        },
      });
  }

  openDetail(inv: AdminInvoiceSummary): void {
    this.detailLoading.set(true);
    this.detailError.set(null);

    this.adminInvoicesService.getInvoiceDetail(inv.id).subscribe({
      next: (detail) => {
        this.selectedInvoice.set(detail);
        this.detailLoading.set(false);
        queueMicrotask(() => {
          this.detailHeading()?.nativeElement.focus();
        });
      },
      error: (err: HttpErrorResponse) => {
        this.detailLoading.set(false);
        this.detailError.set(
          err.error?.detail ?? `No pudimos cargar el detalle de la factura ${inv.numero}.`
        );
      },
    });
  }

  closeDetail(): void {
    this.selectedInvoice.set(null);
    this.detailError.set(null);
  }

  isBusy(id: number, kind: 'pdf' | 'xml' | 'email'): boolean {
    const busy = this.busyAction();
    return busy !== null && busy.id === id && busy.kind === kind;
  }

  downloadFile(inv: Pick<AdminInvoiceSummary, 'id' | 'numero'>, kind: 'pdf' | 'xml'): void {
    this.actionMessage.set(null);
    this.actionError.set(null);
    this.busyAction.set({ id: inv.id, kind });

    const req$ =
      kind === 'pdf'
        ? this.invoiceService.downloadPdf(inv.id)
        : this.invoiceService.downloadXml(inv.id);

    req$.subscribe({
      next: (blob) => {
        this.busyAction.set(null);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${inv.numero}.${kind}`;
        link.click();
        URL.revokeObjectURL(url);
        this.actionMessage.set(`Archivo ${inv.numero}.${kind} descargado.`);
      },
      error: () => {
        this.busyAction.set(null);
        this.actionError.set(
          `No fue posible descargar el archivo ${kind.toUpperCase()} de ${inv.numero}.`
        );
      },
    });
  }

  resendEmail(inv: Pick<AdminInvoiceSummary, 'id' | 'numero'>): void {
    this.actionMessage.set(null);
    this.actionError.set(null);
    this.busyAction.set({ id: inv.id, kind: 'email' });

    this.invoiceService.resendEmail(inv.id).subscribe({
      next: (res) => {
        this.busyAction.set(null);
        this.invoices.update((rows) =>
          rows.map((item) =>
            item.id === inv.id
              ? { ...item, correos_enviados: res.correos_enviados }
              : item
          )
        );
        const currentDetail = this.selectedInvoice();
        if (currentDetail && currentDetail.id === inv.id) {
          this.selectedInvoice.set({
            ...currentDetail,
            correos_enviados: res.correos_enviados,
            ultimo_envio_correo: res.ultimo_envio_correo,
          });
        }
        this.actionMessage.set(`${inv.numero}: ${res.detail}`);
      },
      error: (err: HttpErrorResponse) => {
        this.busyAction.set(null);
        this.actionError.set(
          err.error?.detail ?? `No pudimos reenviar por correo la factura ${inv.numero}.`
        );
      },
    });
  }

  getDianMeta(status: string): DianBadgeMeta {
    return (
      DIAN_STATUS_META[status] ?? {
        label: status,
        icon: '•',
        toneClass: 'dian--neutral',
      }
    );
  }
}
