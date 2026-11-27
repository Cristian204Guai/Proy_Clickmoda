import { CurrencyPipe, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  AdminOrder,
  AdminOrderStatus,
  AdminOrdersService,
} from '../../../core/services/admin-orders.service';

export const ALLOWED_ORDER_TRANSITIONS: Record<AdminOrderStatus, AdminOrderStatus[]> = {
  PENDIENTE: ['PAGADA', 'CANCELADA'],
  PAGADA: ['EN_PREPARACION', 'CANCELADA'],
  EN_PREPARACION: ['ENVIADA', 'CANCELADA'],
  ENVIADA: ['ENTREGADA'],
  ENTREGADA: [],
  CANCELADA: [],
};

export const ORDER_STATUS_LABELS: Record<AdminOrderStatus, string> = {
  PENDIENTE: 'Pendiente',
  PAGADA: 'Pagada',
  EN_PREPARACION: 'En preparación',
  ENVIADA: 'Enviada',
  ENTREGADA: 'Entregada',
  CANCELADA: 'Cancelada',
};

@Component({
  selector: 'app-admin-orders',
  imports: [ReactiveFormsModule, RouterLink, CurrencyPipe, DatePipe],
  templateUrl: './admin-orders.component.html',
  styleUrl: './admin-orders.component.css',
})
export class AdminOrdersComponent implements OnInit {
  private readonly adminOrders = inject(AdminOrdersService);
  private readonly fb = inject(NonNullableFormBuilder);

  readonly allStatuses: AdminOrderStatus[] = [
    'PENDIENTE',
    'PAGADA',
    'EN_PREPARACION',
    'ENVIADA',
    'ENTREGADA',
    'CANCELADA',
  ];

  readonly orders = signal<AdminOrder[]>([]);
  readonly totalCount = signal(0);
  readonly loading = signal(false);
  readonly loadingDetail = signal(false);
  readonly updatingStatus = signal(false);
  readonly selectedOrder = signal<AdminOrder | null>(null);
  readonly feedbackMessage = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);

  readonly pageSize = 8;
  readonly currentPage = signal(1);
  readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.totalCount() / this.pageSize)),
  );
  readonly pageNumbers = computed(() =>
    Array.from({ length: this.totalPages() }, (_, idx) => idx + 1),
  );

  readonly filterForm = this.fb.group({
    search: [''],
    estado: [''],
  });

  readonly statusControl = this.fb.control<AdminOrderStatus | ''>('');

  ngOnInit(): void {
    this.loadOrders();
  }

  loadOrders(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    const { search, estado } = this.filterForm.getRawValue();

    this.adminOrders
      .getOrders({
        search,
        estado,
        page: this.currentPage(),
      })
      .subscribe({
        next: (res) => {
          this.orders.set(res.results);
          this.totalCount.set(res.count);
          this.loading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.loading.set(false);
          this.errorMessage.set(
            err.error?.detail ?? 'No fue posible cargar las órdenes.',
          );
        },
      });
  }

  applyFilters(): void {
    this.currentPage.set(1);
    this.loadOrders();
  }

  clearFilters(): void {
    this.filterForm.reset({ search: '', estado: '' });
    this.currentPage.set(1);
    this.loadOrders();
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages() || page === this.currentPage()) return;
    this.currentPage.set(page);
    this.loadOrders();
  }

  selectOrder(order: AdminOrder): void {
    this.feedbackMessage.set(null);
    this.errorMessage.set(null);
    this.loadingDetail.set(true);
    this.selectedOrder.set(order);
    this.syncStatusControl(order.estado);

    this.adminOrders.getOrder(order.id).subscribe({
      next: (fullOrder) => {
        this.selectedOrder.set(fullOrder);
        this.syncStatusControl(fullOrder.estado);
        this.loadingDetail.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.loadingDetail.set(false);
        this.errorMessage.set(
          err.error?.detail ?? `No se pudo cargar el detalle de la orden #${order.id}.`,
        );
      },
    });
  }

  closeDetail(): void {
    this.selectedOrder.set(null);
    this.statusControl.setValue('');
  }

  getValidTransitions(estado: AdminOrderStatus): AdminOrderStatus[] {
    return ALLOWED_ORDER_TRANSITIONS[estado] ?? [];
  }

  getStatusLabel(estado: AdminOrderStatus): string {
    return ORDER_STATUS_LABELS[estado] ?? estado;
  }

  getStatusBadgeClass(estado: AdminOrderStatus): string {
    return `status-badge status-badge--${estado.toLowerCase()}`;
  }

  updateSelectedOrderStatus(): void {
    const order = this.selectedOrder();
    const targetStatus = this.statusControl.value;
    if (!order || !targetStatus || this.updatingStatus()) return;

    this.updatingStatus.set(true);
    this.feedbackMessage.set(null);
    this.errorMessage.set(null);

    this.adminOrders.updateOrderStatus(order.id, targetStatus).subscribe({
      next: (updated) => {
        this.updatingStatus.set(false);
        this.selectedOrder.set(updated);
        this.syncStatusControl(updated.estado);
        this.orders.update((list) =>
          list.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.feedbackMessage.set(
          `Orden #${updated.id} actualizada a ${this.getStatusLabel(updated.estado)}.`,
        );
      },
      error: (err: HttpErrorResponse) => {
        this.updatingStatus.set(false);
        this.errorMessage.set(
          err.error?.detail ?? `No se pudo actualizar el estado de la orden #${order.id}.`,
        );
      },
    });
  }

  private syncStatusControl(currentStatus: AdminOrderStatus): void {
    const transitions = this.getValidTransitions(currentStatus);
    this.statusControl.setValue(transitions[0] ?? '');
  }
}
