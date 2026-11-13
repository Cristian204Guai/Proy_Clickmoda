import { CurrencyPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { CartItem, CartService } from '../../../core/services/cart.service';

@Component({
  selector: 'app-cart',
  imports: [RouterLink, FormsModule, CurrencyPipe],
  templateUrl: './cart.component.html',
  styleUrls: ['./cart.component.css'],
})
export class CartComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly cartService = inject(CartService);
  private readonly router = inject(Router);

  readonly cart = this.cartService.cart;
  readonly loading = signal(false);
  readonly updatingItemId = signal<number | null>(null);
  readonly applyingCoupon = signal(false);

  readonly stockError = signal<string | null>(null);
  readonly couponMessage = signal<string | null>(null);
  readonly couponError = signal<string | null>(null);

  couponCode = '';

  ngOnInit(): void {
    this.loading.set(true);
    this.cartService.loadCart().subscribe({
      next: (c) => {
        this.couponCode = c.cupon_codigo ?? '';
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  changeQuantity(item: CartItem, delta: number): void {
    const nuevaCantidad = item.cantidad + delta;
    if (nuevaCantidad < 1) {
      return;
    }

    this.stockError.set(null);

    if (nuevaCantidad > item.stock_disponible) {
      this.stockError.set(
        `Solo hay ${item.stock_disponible} unidades disponibles de "${item.nombre_producto}" (${item.talla} · ${item.color}).`
      );
      return;
    }

    this.updatingItemId.set(item.id);
    this.cartService.updateQuantity(item.id, nuevaCantidad).subscribe({
      next: () => this.updatingItemId.set(null),
      error: (err: HttpErrorResponse) => {
        this.updatingItemId.set(null);
        this.stockError.set(
          err.error?.detail ?? 'No se pudo actualizar la cantidad. Verifica el stock disponible.'
        );
        this.cartService.loadCart().subscribe();
      },
    });
  }

  removeItem(item: CartItem): void {
    this.stockError.set(null);
    this.updatingItemId.set(item.id);
    this.cartService.removeItem(item.id).subscribe({
      next: () => this.updatingItemId.set(null),
      error: () => this.updatingItemId.set(null),
    });
  }

  onCouponInput(): void {
    if (this.couponError()) {
      this.couponError.set(null);
    }
  }

  applyCoupon(): void {
    this.couponError.set(null);
    this.couponMessage.set(null);
    this.applyingCoupon.set(true);

    this.cartService.applyCoupon(this.couponCode).subscribe({
      next: (c) => {
        this.applyingCoupon.set(false);
        if (c.cupon_codigo) {
          this.couponMessage.set(`Cupón ${c.cupon_codigo} aplicado correctamente.`);
        } else {
          this.couponMessage.set('Cupón removido.');
        }
      },
      error: (err: HttpErrorResponse) => {
        this.applyingCoupon.set(false);
        this.couponError.set(err.error?.detail ?? 'El cupón ingresado no es válido.');
      },
    });
  }

  goToCheckout(): void {
    if (this.cart().items.length === 0 || this.cart().alertas_stock.length > 0) {
      return;
    }
    this.router.navigateByUrl('/checkout');
  }
}