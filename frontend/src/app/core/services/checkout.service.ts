import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';
import { CartService } from './cart.service';

export type PaymentMethod = 'TARJETA' | 'PSE' | 'NEQUI_DAVIPLATA' | 'CONTRA_ENTREGA';
export type PaymentSimulationResult = 'APROBADO' | 'RECHAZADO' | 'EXPIRADO';

export interface CreateOrderPayload {
  nombre_completo: string;
  telefono: string;
  direccion: string;
  ciudad: string;
  metodo_pago: PaymentMethod;
  token_pago: string;
  requiere_factura_electronica: boolean;
  tipo_documento?: string;
  numero_documento?: string;
  correo_factura?: string;
}

export interface OrderItemResponse {
  id: number;
  variante: number;
  nombre_producto: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: number;
  porcentaje_iva: number;
  subtotal: number;
}

export interface PaymentSummary {
  id: number;
  pasarela: string;
  referencia: string;
  estado: 'PENDIENTE' | 'APROBADO' | 'RECHAZADO' | 'EXPIRADO';
  monto: number;
  mensaje_respuesta: string;
  actualizado_en: string;
}

export interface OrderResponse {
  id: number;
  estado: 'PENDIENTE' | 'PAGADA' | 'EN_PREPARACION' |'ENVIADA'| 'ENTREGADA' | 'CANCELADA';
  metodo_pago: PaymentMethod;
  token_pago: string;
  stock_descontado: boolean;

  // agregar datos de facturación electrónica si requiere_factura_electronica es true
  factura_id?: number | null;
  factura_numero?: string | null;

  subtotal: number;
  envio: number;
  impuestos: number;
  descuento: number;
  total: number;
  cupon_codigo: string;
  requiere_factura_electronica: boolean;
  tipo_documento: string;
  numero_documento: string;
  correo_factura: string;
  direccion_envio: {
    id: number;
    nombre_completo: string;
    telefono: string;
    direccion: string;
    ciudad: string;
  };
  items: OrderItemResponse[];
  payment?: PaymentSummary;
  creado_en: string;
}

@Injectable({ providedIn: 'root' })
export class CheckoutService {
  private readonly http = inject(HttpClient);
  private readonly cartService = inject(CartService);
  private readonly ordersBase = `${API_URL}/orders`;
  private readonly paymentsBase = `${API_URL}/payments`;

  private get headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Cart-Session': this.cartService.sessionKey });
  }

  /**
   * Simula la tokenización en la pasarela desde el navegador (RNF Seguridad / Pagos):
   * nunca almacena ni envía el número completo de tarjeta ni el CVV al backend.
   */
  tokenizeCardInMemory(cardNumber: string, installments: number): string {
    const digits = cardNumber.replace(/\D/g, '');
    const last4 = digits.slice(-4) || '0000';
    const randomToken = Math.random().toString(36).substring(2, 10);
    return `tok_sim_card_${last4}_${installments}c_${randomToken}`;
  }

  createOrder(payload: CreateOrderPayload): Observable<OrderResponse> {
    return this.http.post<OrderResponse>(`${this.ordersBase}/`, payload, {
      headers: this.headers,
    });
  }

  getOrderById(id: number): Observable<OrderResponse> {
    return this.http.get<OrderResponse>(`${this.ordersBase}/${id}/`, {
      headers: this.headers,
    });
  }

  /**
   * Llama al endpoint simulador de webhook (POST /api/v1/payments/webhook/)
   * que ejecuta la transacción atómica de confirmación o rechazo de pago.
   */
  simulatePaymentWebhook(
    ordenId: number,
    resultado: PaymentSimulationResult
  ): Observable<OrderResponse> {
    return this.http.post<OrderResponse>(
      `${this.paymentsBase}/webhook/`,
      { orden_id: ordenId, resultado },
      { headers: this.headers }
    );
  }
}