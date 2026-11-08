import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-catalog',
  imports: [RouterLink],
  template: `
    <nav style="display:flex;gap:1rem;padding:1rem;background:#1F2937">
      <strong style="color:#fff">Click<span style="color:#F59E0B">Moda</span></strong>
      @if (auth.isLoggedIn()) {
        <a routerLink="/cuenta" style="color:#fff">Mi cuenta</a>
        @if (auth.isAdmin()) { <a routerLink="/admin" style="color:#fff">Admin</a> }
      } @else {
        <a routerLink="/login" style="color:#fff">Ingresar</a>
      }
    </nav>
    <main style="padding:1rem"><h1>Catálogo (días 5–7)</h1></main>
  `,
})
export class CatalogComponent {
  readonly auth = inject(AuthService);
}