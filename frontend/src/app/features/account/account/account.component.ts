import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-account',
  template: `
    <main style="padding:1.5rem">
      <h1>Mi cuenta</h1>
      <p>Hola, {{ auth.user()?.nombre }} ({{ auth.user()?.email }})</p>
      <button type="button" (click)="logout()">Cerrar sesión</button>
    </main>
  `,
})
export class AccountComponent {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  logout(): void {
    this.auth.logout();
    this.router.navigateByUrl('/login');
  }
}
