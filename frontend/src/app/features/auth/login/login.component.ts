import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
  
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
