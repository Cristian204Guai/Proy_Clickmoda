import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { API_URL } from '../api.config';

export interface CartItem {
  id: number;
  variante_id: number;
  producto_id: number;
  nombre_producto: string;
  talla: string;
  color: string;
  color_hex: string;
  precio_unitario: number;
  cantidad: number;
  stock_disponible: number;
  imagen_url: string;
  subtotal: number;
  sin_stock: boolean;
}

export interface Cart {
  id: number;
  items: CartItem[];
  total_unidades: number;
  subtotal: number;
  envio: number;
  iva: number;
  descuento: number;
  total: number;
  cupon_codigo: string | null;
  alertas_stock: string[];
}

const CART_SESSION_KEY = 'cm_cart_session';

const EMPTY_CART: Cart = {
  id: 0,
  items: [],
  total_unidades: 0,
  subtotal: 0,
  envio: 0,
  iva: 0,
  descuento: 0,
  total: 0,
  cupon_codigo: null,
  alertas_stock: [],
};

@Injectable({ providedIn: 'root' })
export class CartService {
  private readonly http = inject(HttpClient);
  private readonly base = `${API_URL}/cart`;

  private readonly _cart = signal<Cart>(EMPTY_CART);
  readonly cart = this._cart.asReadonly();
  readonly totalUnits = computed(() => this._cart().total_unidades);

  get sessionKey(): string {
    let key = localStorage.getItem(CART_SESSION_KEY);
    if (!key) {
      key = 'guest-' + Math.random().toString(36).substring(2, 12) + '-' + Date.now();
      localStorage.setItem(CART_SESSION_KEY, key);
    }
    return key;
  }

  private get headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Cart-Session': this.sessionKey });
  }

  loadCart(): Observable<Cart> {
    return this.http
      .get<Cart>(`${this.base}/`, { headers: this.headers })
      .pipe(tap((c) => this._cart.set(c)));
  }

  addItem(varianteId: number, cantidad = 1): Observable<Cart> {
    return this.http
      .post<Cart>(
        `${this.base}/items/`,
        { variante_id: varianteId, cantidad },
        { headers: this.headers }
      )
      .pipe(tap((c) => this._cart.set(c)));
  }

  updateQuantity(itemId: number, cantidad: number): Observable<Cart> {
    return this.http
      .patch<Cart>(
        `${this.base}/items/${itemId}/`,
        { cantidad },
        { headers: this.headers }
      )
      .pipe(tap((c) => this._cart.set(c)));
  }

  removeItem(itemId: number): Observable<Cart> {
    return this.http
      .delete<Cart>(`${this.base}/items/${itemId}/`, { headers: this.headers })
      .pipe(tap((c) => this._cart.set(c)));
  }

  applyCoupon(codigo: string): Observable<Cart> {
    return this.http
      .post<Cart>(
        `${this.base}/coupon/`,
        { codigo },
        { headers: this.headers }
      )
      .pipe(tap((c) => this._cart.set(c)));
  }

  /** RF-10: Fusiona el carrito del visitante con el carrito del usuario autenticado */
  mergeGuestCart(): Observable<Cart> {
    return this.http
      .post<Cart>(
        `${this.base}/merge/`,
        { session_key: this.sessionKey },
        { headers: this.headers }
      )
      .pipe(tap((c) => this._cart.set(c)));
  }
}