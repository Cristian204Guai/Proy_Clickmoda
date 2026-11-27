import { CurrencyPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import {
  CatalogService,
  Category,
  Product,
  SizeOption,
} from '../../../core/services/catalog.service';
import { CartService } from '../../../core/services/cart.service';

interface ColorOption {
  name: string;
  hex: string;
  borderClass: string;
}

@Component({
  selector: 'app-catalog',
  imports: [RouterLink, FormsModule, CurrencyPipe],
  templateUrl: './catalog.component.html',
})
export class CatalogComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly catalogService = inject(CatalogService);

  readonly categories = signal<Category[]>([]);
  readonly products = signal<Product[]>([]);
  readonly totalCount = signal(0);
  readonly loading = signal(false);
  readonly mobileFiltersOpen = signal(false);
  private readonly cartService = inject(CartService);
  readonly cartCount = this.cartService.totalUnits; // Valor visual del prototipo hasta conectar Carrito en Días 8-10


  // Estado de filtros
  readonly selectedCategories = signal<string[]>([]);
  readonly selectedSize = signal<SizeOption | ''>('');
  readonly selectedColor = signal<string>('');
  minPrice: number | null = null;
  maxPrice: number | null = null;
  searchText = '';
  ordering = '-creado_en';

  // Paginación (8 prendas por página como en el prototipo)
  readonly pageSize = 8;
  readonly currentPage = signal(1);
  readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.totalCount() / this.pageSize))
  );
  readonly pageNumbers = computed(() =>
    Array.from({ length: this.totalPages() }, (_, i) => i + 1)
  );

  readonly sizes: SizeOption[] = ['XS', 'S', 'M', 'L', 'XL'];
  readonly colors: ColorOption[] = [
    { name: 'Negro', hex: '#111827', borderClass: 'border-gray-700' },
    { name: 'Azul', hex: '#1D4ED8', borderClass: 'border-blue-800' },
    { name: 'Ámbar', hex: '#F59E0B', borderClass: 'border-amber-600' },
    { name: 'Blanco', hex: '#FFFFFF', borderClass: 'border-gray-400' },
  ];

  ngOnInit(): void {
    this.cartService.loadCart().subscribe();
    this.catalogService.getCategories().subscribe({
      next: (cats) => this.categories.set(cats),
    });
    this.loadProducts();
  }

  toggleCategory(slug: string): void {
    const current = this.selectedCategories();
    if (current.includes(slug)) {
      this.selectedCategories.set(current.filter((item) => item !== slug));
    } else {
      this.selectedCategories.set([...current, slug]);
    }
  }

  toggleSize(size: SizeOption): void {
    this.selectedSize.set(this.selectedSize() === size ? '' : size);
  }

  toggleColor(colorName: string): void {
    this.selectedColor.set(this.selectedColor() === colorName ? '' : colorName);
  }

  applyFilters(): void {
    this.currentPage.set(1);
    this.loadProducts();
  }

  onOrderingChange(): void {
    this.currentPage.set(1);
    this.loadProducts();
  }

  quickFilterSearch(term: string): void {
    this.searchText = term;
    this.applyFilters();
  }

  quickOrdering(order: string): void {
    this.ordering = order;
    this.applyFilters();
  }

  clearFilters(): void {
    this.selectedCategories.set([]);
    this.selectedSize.set('');
    this.selectedColor.set('');
    this.minPrice = null;
    this.maxPrice = null;
    this.searchText = '';
    this.ordering = '-creado_en';
    this.currentPage.set(1);
    this.loadProducts();
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.loadProducts();
  }

  loadProducts(): void {
    this.loading.set(true);
    this.catalogService
      .getProducts({
        categories: this.selectedCategories(),
        size: this.selectedSize(),
        color: this.selectedColor(),
        min_price: this.minPrice,
        max_price: this.maxPrice,
        search: this.searchText,
        ordering: this.ordering,
        page: this.currentPage(),
      })
      .subscribe({
        next: (res) => {
          this.products.set(res.results);
          this.totalCount.set(res.count);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
        },
      });
  }

  getProductPreviewImage(product: Product): string | null {
    const firstImg = product.imagenes?.[0]?.url?.trim();
    if (!firstImg) return null;
    if (
      firstImg.startsWith('http://') ||
      firstImg.startsWith('https://') ||
      firstImg.startsWith('/media/') ||
      firstImg.startsWith('data:')
    ) {
      return firstImg;
    }
    return null;
  }

  getProductPreviewColor(product: Product): string {
    const firstImg = product.imagenes?.[0]?.url?.trim();
    return firstImg && firstImg.startsWith('#') ? firstImg : '#CBD5E1';
  }

  formatSizesLabel(sizes: SizeOption[]): string {
    if (!sizes || sizes.length === 0) return 'Sin stock';
    if (sizes.length === 1) return `Talla ${sizes[0]}`;
    return `Tallas ${sizes[0]} - ${sizes[sizes.length - 1]}`;
  }

  addToCartPreview(product: Product): void {
    const sizeFilter = this.selectedSize();
    const colorFilter = this.selectedColor();
    const variant =
      product.variantes.find(
        (v) =>
          v.stock > 0 &&
          (!sizeFilter || v.talla === sizeFilter) &&
          (!colorFilter || v.color === colorFilter)
      ) ?? product.variantes.find((v) => v.stock > 0);
    if (!variant) return;
    this.cartService.addItem(variant.id, 1).subscribe();
  }
}