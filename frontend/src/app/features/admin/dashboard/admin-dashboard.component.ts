import { CurrencyPipe, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  AdminDashboardService,
  AdminStats,
} from '../../../core/services/admin-dashboard.service';

interface StatusDisplay {
  label: string;
  icon: string;
  toneClass: string;
}

const ORDER_STATUS_MAP: Record<string, StatusDisplay> = {
  PENDIENTE: { label: 'Pendiente', icon: '⏳', toneClass: 'badge--pending' },
  PAGADA: { label: 'Pagada', icon: '✓', toneClass: 'badge--paid' },
  EN_PREPARACION: { label: 'En preparación', icon: '✂', toneClass: 'badge--prep' },
  ENVIADA: { label: 'Enviada', icon: '📦', toneClass: 'badge--shipped' },
  ENTREGADA: { label: 'Entregada', icon: '★', toneClass: 'badge--delivered' },
  CANCELADA: { label: 'Cancelada', icon: '✕', toneClass: 'badge--cancelled' },
};

@Component({
  selector: 'app-admin-dashboard',
  imports: [CurrencyPipe, DatePipe, RouterLink],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.css'],
})
export class AdminDashboardComponent implements OnInit {
  private readonly dashboardService = inject(AdminDashboardService);

  readonly stats = signal<AdminStats | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.loadStats();
  }

  loadStats(): void {
    this.loading.set(true);
    this.error.set(null);

    this.dashboardService.getStats().subscribe({
      next: (data) => {
        this.stats.set(data);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(
          err.error?.detail ?? 'No pudimos cargar las estadísticas del panel de administración.'
        );
        this.loading.set(false);
      },
    });
  }

  getOrderStatus(estado: string): StatusDisplay {
    return (
      ORDER_STATUS_MAP[estado] ?? {
        label: estado,
        icon: '•',
        toneClass: 'badge--neutral',
      }
    );
  }
}
