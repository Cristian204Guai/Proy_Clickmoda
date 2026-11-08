import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <main class="auth">
      <h1>Iniciar sesión</h1>
      <form [formGroup]="form" (ngSubmit)="submit()" novalidate [attr.aria-busy]="loading()">
        <label for="email">Correo electrónico</label>
        <input id="email" type="email" formControlName="email" autocomplete="email"
               [attr.aria-invalid]="form.controls.email.touched && form.controls.email.invalid" />
        @if (form.controls.email.touched && form.controls.email.invalid) {
          <p class="field-error">Ingresa un correo válido.</p>
        }

        <label for="password">Contraseña</label>
        <input id="password" type="password" formControlName="password" autocomplete="current-password"
               [attr.aria-invalid]="form.controls.password.touched && form.controls.password.invalid" />
        @if (form.controls.password.touched && form.controls.password.invalid) {
          <p class="field-error">La contraseña es obligatoria.</p>
        }

        @if (error()) { <p class="form-error" role="alert">{{ error() }}</p> }

        <button type="submit" [disabled]="loading()">
          {{ loading() ? 'Ingresando…' : 'Ingresar' }}
        </button>
      </form>
      <p>¿No tienes cuenta? <a routerLink="/registro">Regístrate</a></p>
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
    .field-error, .form-error { color: #b91c1c; margin: 0; font-size: .875rem; }
    button { margin-top: 1rem; padding: .7rem; border: 0; border-radius: .5rem; cursor: pointer;
             background: var(--color-primary, #2563EB); color: #fff; font-weight: 600; }
    button:disabled { opacity: .6; cursor: not-allowed; }
    a { color: var(--color-primary, #2563EB); }
  `],
})
export class LoginComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading.set(true);
    this.error.set(null);
    this.auth.login(this.form.getRawValue()).subscribe({
      next: (user) => {
        const ret = this.route.snapshot.queryParamMap.get('returnUrl');
        // solo rutas internas (evita open redirect)
        const safe = ret && ret.startsWith('/') && !ret.startsWith('//') ? ret : null;
        this.router.navigateByUrl(safe ?? (user.role === 'ADMIN' ? '/admin' : '/cuenta'));
      },
      error: (e: HttpErrorResponse) => {
        this.loading.set(false);
        this.error.set(
          e.status === 429 ? 'Demasiados intentos. Espera un minuto e inténtalo de nuevo.'
          : e.status === 401 ? 'Correo o contraseña incorrectos.'
          : 'No pudimos iniciar sesión. Intenta más tarde.',
        );
      },
    });
  }
}
