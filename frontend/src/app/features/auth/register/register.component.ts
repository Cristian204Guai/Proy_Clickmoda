import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-register',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
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