import { CurrencyPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import {
  NonNullableFormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { CartService } from '../../../core/services/cart.service';
import {
  CheckoutService,
  OrderResponse,
  PaymentMethod,
} from '../../../core/services/checkout.service';

export type CheckoutStep = 2 | 3 | 4;

@Component({
  selector: 'app-checkout',
  imports: [RouterLink, ReactiveFormsModule, CurrencyPipe],
  templateUrl: './checkout.component.html',
  styleUrls: ['./checkout.component.css'],
})
export class CheckoutComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly cartService = inject(CartService);
  private readonly checkoutService = inject(CheckoutService);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly router = inject(Router);

  readonly cart = this.cartService.cart;
  readonly activeStep = signal<CheckoutStep>(3); // En el prototipo (pág. 3) están visibles Envío y 3 Pago activo
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);
  readonly createdOrder = signal<OrderResponse | null>(null);

  /**
   * Formulario reactivo estrictamente tipado.
   * Los datos de tarjeta (numeroTarjeta, cvv, etc.) solo existen en memoria del DOM
   * para validar formato y generar un token simulado; jamás se persisten ni envían.
   */
  readonly checkoutForm = this.fb.group({
    // Sección Dirección de envío (RF-11)
    nombreCompleto: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(150)]],
    telefono: ['', [Validators.required, Validators.pattern(/^[0-9+\s()-]{7,20}$/)]],
    direccion: ['', [Validators.required, Validators.minLength(5), Validators.maxLength(255)]],
    ciudad: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],

    // Sección Método de pago (RF-12)
    metodoPago: ['TARJETA' as PaymentMethod, [Validators.required]],

    // Campos exclusivos de Tarjeta (solo en memoria, nunca enviados al backend)
    numeroTarjeta: ['', [Validators.required, Validators.pattern(/^[\d ]{13,19}$/)]],
    nombreTarjeta: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(60)]],
    vencimiento: ['', [Validators.required, Validators.pattern(/^(0[1-9]|1[0-2])\/\d{2}$/)]],
    cvv: ['', [Validators.required, Validators.pattern(/^\d{3,4}$/)]],
    cuotas: [1, [Validators.required, Validators.min(1), Validators.max(36)]],

    // Campos opcionales para PSE / Billeteras
    bancoPse: ['Bancolombia'],
    celularBilletera: [''],

    // Casilla Factura Electrónica DIAN (RF-16)
    requiereFacturaElectronica: [true],
    tipoDocumento: ['CC'],
    numeroDocumento: [''],
    correoFactura: ['', [Validators.email]],
  });

  ngOnInit(): void {
    this.cartService.loadCart().subscribe();

    // Prellenar nombre, teléfono y correo si el cliente inició sesión
    const user = this.auth.user();
    if (user) {
      this.checkoutForm.patchValue({
        nombreCompleto: user.nombre || '',
        telefono: user.telefono || '',
        correoFactura: user.email || '',
      });
    }

    // Ajustar validadores dinámicamente al cambiar el método de pago
    this.checkoutForm.controls.metodoPago.valueChanges.subscribe((method) => {
      this.updatePaymentValidators(method);
    });
  }

  setStep(step: CheckoutStep): void {
    this.activeStep.set(step);
  }

  selectPaymentMethod(method: PaymentMethod): void {
    this.checkoutForm.controls.metodoPago.setValue(method);
    this.activeStep.set(3);
  }

  formatCardNumberInput(): void {
    const raw = this.checkoutForm.controls.numeroTarjeta.value;
    const digits = raw.replace(/\D/g, '').slice(0, 16);
    const grouped = digits.replace(/(\d{4})(?=\d)/g, '$1 ');
    if (grouped !== raw) {
      this.checkoutForm.controls.numeroTarjeta.setValue(grouped, { emitEvent: false });
    }
  }

  formatExpiryInput(): void {
    const raw = this.checkoutForm.controls.vencimiento.value;
    const digits = raw.replace(/\D/g, '').slice(0, 4);
    const formatted =
      digits.length >= 3 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
    if (formatted !== raw) {
      this.checkoutForm.controls.vencimiento.setValue(formatted, { emitEvent: false });
    }
  }

  private updatePaymentValidators(method: PaymentMethod): void {
    const { numeroTarjeta, nombreTarjeta, vencimiento, cvv, cuotas } =
      this.checkoutForm.controls;

    if (method === 'TARJETA') {
      numeroTarjeta.setValidators([Validators.required, Validators.pattern(/^[\d ]{13,19}$/)]);
      nombreTarjeta.setValidators([Validators.required, Validators.minLength(3), Validators.maxLength(60)]);
      vencimiento.setValidators([Validators.required, Validators.pattern(/^(0[1-9]|1[0-2])\/\d{2}$/)]);
      cvv.setValidators([Validators.required, Validators.pattern(/^\d{3,4}$/)]);
      cuotas.setValidators([Validators.required, Validators.min(1), Validators.max(36)]);
    } else {
      // Limpiar datos sensibles y desactivar validadores cuando no se usa tarjeta
      numeroTarjeta.clearValidators();
      nombreTarjeta.clearValidators();
      vencimiento.clearValidators();
      cvv.clearValidators();
      cuotas.clearValidators();
      this.checkoutForm.patchValue(
        { numeroTarjeta: '', nombreTarjeta: '', vencimiento: '', cvv: '' },
        { emitEvent: false }
      );
    }

    [numeroTarjeta, nombreTarjeta, vencimiento, cvv, cuotas].forEach((ctrl) =>
      ctrl.updateValueAndValidity({ emitEvent: false })
    );
  }

  isInvalid(
    controlName: keyof CheckoutComponent['checkoutForm']['controls']
  ): boolean {
    const control = this.checkoutForm.controls[controlName];
    return control.touched && control.invalid;
  }

  submitCheckout(): void {
    this.submitError.set(null);

    if (this.cart().items.length === 0) {
      this.submitError.set('Tu carrito está vacío. Agrega prendas antes de pagar.');
      return;
    }

    if (this.checkoutForm.invalid) {
      this.checkoutForm.markAllAsTouched();
      this.submitError.set('Por favor revisa los campos obligatorios marcados en rojo.');
      return;
    }

    const raw = this.checkoutForm.getRawValue();

    // Generar token simulado de pasarela sin guardar ni enviar jamás número de tarjeta ni CVV
    let tokenPago = '';
    if (raw.metodoPago === 'TARJETA') {
      tokenPago = this.checkoutService.tokenizeCardInMemory(
        raw.numeroTarjeta,
        Number(raw.cuotas) || 1
      );
      // Borrar inmediatamente de memoria el número de tarjeta y el CVV
      this.checkoutForm.patchValue({ numeroTarjeta: '', cvv: '' }, { emitEvent: false });
    } else if (raw.metodoPago === 'PSE') {
      tokenPago = `tok_sim_pse_${raw.bancoPse.toLowerCase().replace(/\s+/g, '_')}`;
    } else if (raw.metodoPago === 'NEQUI_DAVIPLATA') {
      tokenPago = `tok_sim_wallet`;
    } else {
      tokenPago = `contra_entrega`;
    }

    this.submitting.set(true);

    this.checkoutService
      .createOrder({
        nombre_completo: raw.nombreCompleto.trim(),
        telefono: raw.telefono.trim(),
        direccion: raw.direccion.trim(),
        ciudad: raw.ciudad.trim(),
        metodo_pago: raw.metodoPago,
        token_pago: tokenPago,
        requiere_factura_electronica: raw.requiereFacturaElectronica,
        tipo_documento: raw.tipoDocumento || 'CC',
        numero_documento: raw.numeroDocumento.trim(),
        correo_factura: raw.correoFactura.trim(),
      })
      .subscribe({
        next: (order) => {
          this.submitting.set(false);
          this.createdOrder.set(order);
          this.activeStep.set(4);
        },
        error: (err: HttpErrorResponse) => {
          this.submitting.set(false);
          this.submitError.set(
            err.error?.detail ?? 'No pudimos procesar tu pedido. Verifica los datos e intenta nuevamente.'
          );
        },
      });
  }

  continueShopping(): void {
    this.router.navigateByUrl('/');
  }
}