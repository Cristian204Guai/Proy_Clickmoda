import { CurrencyPipe, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { CartService } from '../../../core/services/cart.service';
import { InvoiceDetail, InvoiceService } from '../../../core/services/invoice.service';

@Component({
  selector: 'app-invoice-detail',
  imports: [RouterLink, CurrencyPipe, DatePipe],
  templateUrl: './invoice-detail.component.html',
  styleUrls: ['./invoice-detail.component.css'],
})
export class InvoiceDetailComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly cartService = inject(CartService);
  private readonly invoiceService = inject(InvoiceService);
  private readonly route = inject(ActivatedRoute);

  readonly invoice = signal<InvoiceDetail | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly actionMessage = signal<string | null>(null);
  readonly actionError = signal<string | null>(null);
  readonly resending = signal(false);
  readonly downloading = signal<'pdf' | 'xml' | null>(null);

  /** Matriz 11x11 determinística para renderizar el código QR simulado desde el CUFE */
  readonly qrCells = computed(() => {
    const cufe = this.invoice()?.cufe ?? '';
    const cells: { x: number; y: number }[] = [];
    for (let row = 0; row < 11; row++) {
      for (let col = 0; col < 11; col++) {
        const isCornerFinder =
          (row < 3 && col < 3) || (row < 3 && col > 7) || (row > 7 && col < 3);
        const charCode = cufe.charCodeAt((row * 11 + col) % Math.max(cufe.length, 1)) || 0;
        if (isCornerFinder || charCode % 2 === 0) {
          cells.push({ x: col * 8 + 6, y: row * 8 + 6 });
        }
      }
    }
    return cells;
  });

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) {
      this.error.set('Número de factura inválido.');
      this.loading.set(false);
      return;
    }

    this.invoiceService.getInvoice(id).subscribe({
      next: (data) => {
        this.invoice.set(data);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(err.error?.detail ?? 'No pudimos cargar la factura electrónica.');
        this.loading.set(false);
      },
    });
  }

  downloadFile(kind: 'pdf' | 'xml'): void {
    const inv = this.invoice();
    if (!inv) return;

    this.actionError.set(null);
    this.actionMessage.set(null);
    this.downloading.set(kind);

    const request$ =
      kind === 'pdf'
        ? this.invoiceService.downloadPdf(inv.id)
        : this.invoiceService.downloadXml(inv.id);

    request$.subscribe({
      next: (blob) => {
        this.downloading.set(null);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${inv.numero}.${kind}`;
        link.click();
        URL.revokeObjectURL(url);
        this.actionMessage.set(`Archivo ${inv.numero}.${kind} descargado.`);
      },
      error: () => {
        this.downloading.set(null);
        this.actionError.set(`No fue posible descargar el archivo ${kind.toUpperCase()}.`);
      },
    });
  }

  resendEmail(): void {
    const inv = this.invoice();
    if (!inv) return;

    this.actionError.set(null);
    this.actionMessage.set(null);
    this.resending.set(true);

    this.invoiceService.resendEmail(inv.id).subscribe({
      next: (res) => {
        this.resending.set(false);
        this.actionMessage.set(res.detail);
      },
      error: (err: HttpErrorResponse) => {
        this.resending.set(false);
        this.actionError.set(
          err.error?.detail ?? 'No pudimos reenviar la factura por correo.'
        );
      },
    });
  }
}