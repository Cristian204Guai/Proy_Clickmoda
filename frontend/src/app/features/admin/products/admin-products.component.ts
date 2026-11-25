import { CurrencyPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { API_URL } from '../../../core/api.config';
import {
  AdminCatalogService,
  AdminCategory,
  AdminProduct,
  AdminProductEstado,
  AdminProductEstadoFilter,
} from '../../../core/services/admin-catalog.service';

const API_ORIGIN = API_URL.replace(/\/api\/v1\/?$/, '');

@Component({
  selector: 'app-admin-products',
  imports: [ReactiveFormsModule, RouterLink, CurrencyPipe],
  templateUrl: './admin-products.component.html',
  styleUrl: './admin-products.component.css',
})
export class AdminProductsComponent implements OnInit {
  private readonly adminCatalog = inject(AdminCatalogService);
  private readonly fb = inject(NonNullableFormBuilder);

  readonly categories = signal<AdminCategory[]>([]);
  readonly products = signal<AdminProduct[]>([]);
  readonly totalCount = signal(0);
  readonly loading = signal(false);
  readonly deleting = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly feedbackMessage = signal<string | null>(null);
  readonly pendingDelete = signal<AdminProduct | null>(null);

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
    category: [''],
    estado: ['' as AdminProductEstadoFilter],
  });

  ngOnInit(): void {
    this.loadCategories();
    this.loadProducts();
  }

  loadCategories(): void {
    this.adminCatalog.getCategories().subscribe({
      next: (cats) => this.categories.set(cats),
    });
  }

  loadProducts(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    const { search, category, estado } = this.filterForm.getRawValue();

    this.adminCatalog
      .getProducts({
        search,
        category,
        estado,
        page: this.currentPage(),
      })
      .subscribe({
        next: (res) => {
          this.products.set(res.results);
          this.totalCount.set(res.count);
          this.loading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.loading.set(false);
          this.errorMessage.set(
            err.error?.detail ?? 'No fue posible cargar el listado de productos.',
          );
        },
      });
  }

  applyFilters(): void {
    this.currentPage.set(1);
    this.loadProducts();
  }

  clearFilters(): void {
    this.filterForm.reset({ search: '', category: '', estado: '' });
    this.currentPage.set(1);
    this.loadProducts();
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages() || page === this.currentPage()) return;
    this.currentPage.set(page);
    this.loadProducts();
  }

  getPreviewImage(product: AdminProduct): string | null {
    const raw = product.imagenes?.[0]?.url?.trim();
    if (!raw) return null;
    if (raw.startsWith('http://') || raw.startsWith('https://') || raw.startsWith('data:')) {
      return raw;
    }
    if (raw.startsWith('/media/')) {
      return `${API_ORIGIN}${raw}`;
    }
    return null;
  }

  getPreviewColor(product: AdminProduct): string {
    const raw = product.imagenes?.[0]?.url?.trim();
    if (raw && raw.startsWith('#')) {
      return raw;
    }
    return product.variantes?.[0]?.color_hex || '#CBD5E1';
  }

  getStatusClass(estado: AdminProductEstado): string {
    switch (estado) {
      case 'Activo':
        return 'badge--activo';
      case 'Agotado':
        return 'badge--agotado';
      case 'Inactivo':
        return 'badge--inactivo';
    }
  }

  requestDelete(product: AdminProduct): void {
    this.feedbackMessage.set(null);
    this.errorMessage.set(null);
    this.pendingDelete.set(product);
  }

  cancelDelete(): void {
    this.pendingDelete.set(null);
  }

  confirmDelete(): void {
    const target = this.pendingDelete();
    if (!target || this.deleting()) return;

    this.deleting.set(true);
    this.errorMessage.set(null);
    this.feedbackMessage.set(null);

    this.adminCatalog.deleteProduct(target.id).subscribe({
      next: (res) => {
        this.deleting.set(false);
        this.pendingDelete.set(null);

        if (res?.deactivated) {
          this.feedbackMessage.set(
            res.detail ??
              `El producto "${target.nombre}" tiene órdenes asociadas y fue desactivado.`,
          );
        } else {
          this.feedbackMessage.set(`Producto "${target.nombre}" eliminado correctamente.`);
          if (this.products().length === 1 && this.currentPage() > 1) {
            this.currentPage.update((p) => p - 1);
          }
        }

        this.loadProducts();
      },
      error: (err: HttpErrorResponse) => {
        this.deleting.set(false);
        this.pendingDelete.set(null);
        this.errorMessage.set(
          err.error?.detail ?? `No se pudo eliminar o desactivar "${target.nombre}".`,
        );
      },
    });
  }
}
