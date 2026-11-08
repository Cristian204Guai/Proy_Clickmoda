import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-register',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <main class="auth">
      <h1>Crear cuenta</h1>
      <form [formGroup]="form" (ngSubmit)="submit()" novalidate [attr.aria-busy]="loading()">
        <label for="nombre">Nombre completo</label>
        <input id="nombre" formControlName="nombre" autocomplete="name"
               [attr.aria-invalid]="form.controls.nombre.touched && form.controls.nombre.invalid" />
        @if (form.controls.nombre.touched && form.controls.nombre.invalid) {
          <p class="field-error">Ingresa tu nombre.</p>
        }

        <label for="email">Correo electrónico</label>
        <input id="email" type="email" formControlName="email" autocomplete="email"
               [attr.aria-invalid]="form.controls.email.touched && form.controls.email.invalid" />
        @if (form.controls.email.touched && form.controls.email.invalid) {
          <p class="field-error">Ingresa un correo válido.</p>
        }

        <label for="telefono">Teléfono (opcional)</label>
        <input id="telefono" type="tel" formControlName="telefono" autocomplete="tel" />

        <label for="password">Contraseña</label>
        <input id="password" type="password" formControlName="password" autocomplete="new-password"
               aria-describedby="pwd-help"
               [attr.aria-invalid]="form.controls.password.touched && form.controls.password.invalid" />
        <p id="pwd-help" class="help">Mínimo 8 caracteres; evita claves comunes o solo numéricas.</p>
        @if (form.controls.password.touched && form.controls.password.invalid) {
          <p class="field-error">La contraseña debe tener al menos 8 caracteres.</p>
        }

        @if (error()) { <p class="form-error" role="alert">{{ error() }}</p> }

        <button type="submit" [disabled]="loading()">
          {{ loading() ? 'Creando cuenta…' : 'Registrarme' }}
        </button>
      </form>
      <p>¿Ya tienes cuenta? <a routerLink="/login">Inicia sesión</a></p>
    </main>
  `,
  styles: [`
    .auth { max-width: 24rem; margin: 2rem auto; padding: 1.5rem; background: #fff;
            border: 1px solid #e5e7eb; border-radius: .75rem; color: var(--color-text, #111827); }
    form { display: grid; gap: .5rem; }
    label { font-weight: 600; margin-top: .5rem; }
    input { padding: .6rem .75rem; border: 1px solid #9ca3af; border-radius: .5rem; font: inherit; }
    input:focus-visible, button:focus-visible, a:focus-visible { outline: 3px solid var(--color-accent, #F59E0B); outline-offset: 2px; }
    input[aria-invalid='true'] { border-color: #b91c1c; }
    .help { color: #4b5563; margin: 0; font-size: .8rem; }
    .field-error, .form-error { color: #b91c1c; margin: 0; font-size: .875rem; }
    button { margin-top: 1rem; padding: .7rem; border: 0; border-radius: .5rem; cursor: pointer;
             background: var(--color-primary, #2563EB); color: #fff; font-weight: 600; }
    button:disabled { opacity: .6; cursor: not-allowed; }
    a { color: var(--color-primary, #2563EB); }
  `],
})
export class RegisterComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly form = this.fb.group({
    nombre: ['', [Validators.required, Validators.maxLength(150)]],
    email: ['', [Validators.required, Validators.email]],
    telefono: [''],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading.set(true);
    this.error.set(null);
    this.auth.register(this.form.getRawValue()).subscribe({
      next: () => this.router.navigateByUrl('/cuenta'),
      error: (e: HttpErrorResponse) => {
        this.loading.set(false);
        const first = e.status === 400 && e.error
          ? (Object.values(e.error as Record<string, string[]>).flat()[0] as string)
          : null;
        this.error.set(
          e.status === 429 ? 'Demasiados intentos. Espera e inténtalo de nuevo.'
          : first ?? 'No pudimos crear la cuenta. Intenta más tarde.',
        );
      },
    });
  }
}