import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormControl,
  FormGroup,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Observable, of, switchMap } from 'rxjs';
import { API_URL } from '../../../core/api.config';
import {
  AdminCatalogService,
  AdminCategory,
  AdminProduct,
  AdminProductImage,
  AdminProductPayload,
  AdminVariant,
} from '../../../core/services/admin-catalog.service';
import { SizeOption } from '../../../core/services/catalog.service';

const API_ORIGIN = API_URL.replace(/\/api\/v1\/?$/, '');
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const HEX_COLOR_RE = /^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$/;

export type VariantFormGroup = FormGroup<{
  id: FormControl<number | null>;
  talla: FormControl<SizeOption>;
  color: FormControl<string>;
  color_hex: FormControl<string>;
  sku: FormControl<string>;
  stock: FormControl<number>;
}>;

export interface PendingUploadFile {
  id: string;
  file: File;
  previewUrl: string;
  name: string;
  sizeLabel: string;
}

function noDuplicateVariantsValidator(control: AbstractControl): ValidationErrors | null {
  if (!(control instanceof FormArray)) return null;
  const seen = new Map<string, number>();

  for (let i = 0; i < control.length; i++) {
    const group = control.at(i);
    const talla = String(group.get('talla')?.value ?? '').trim();
    const color = String(group.get('color')?.value ?? '').trim().toLowerCase();
    if (!talla || !color) continue;

    const key = `${talla}::${color}`;
    if (seen.has(key)) {
      return {
        duplicateVariant: {
          talla,
          color: String(group.get('color')?.value ?? '').trim(),
        },
      };
    }
    seen.set(key, i);
  }

  return null;
}

@Component({
  selector: 'app-admin-product-form',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './admin-product-form.component.html',
  styleUrl: './admin-product-form.component.css',
})
export class AdminProductFormComponent implements OnInit, OnDestroy {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly adminCatalog = inject(AdminCatalogService);
  private readonly route = inject(ActivatedRoute);
  private readonly formRef = viewChild<ElementRef<HTMLFormElement>>('productFormEl');

  readonly sizes: SizeOption[] = ['XS', 'S', 'M', 'L', 'XL'];
  readonly categories = signal<AdminCategory[]>([]);
  readonly productId = signal<number | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly submitted = signal(false);
  readonly dragActive = signal(false);

  readonly savedImages = signal<AdminProductImage[]>([]);
  readonly manualImages = signal<AdminProductImage[]>([]);
  readonly pendingFiles = signal<PendingUploadFile[]>([]);
  readonly deletingImageId = signal<number | null>(null);

  readonly manualImageInput = new FormControl('', { nonNullable: true });
  readonly manualImageError = signal<string | null>(null);
  readonly imageErrors = signal<string[]>([]);
  readonly feedbackMessage = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);

  readonly productForm = this.fb.group({
    nombre: ['', [Validators.required, Validators.maxLength(180)]],
    descripcion: [''],
    categoria: [0, [Validators.required, Validators.min(1)]],
    precio_base: [0, [Validators.required, Validators.min(0)]],
    porcentaje_iva: [19, [Validators.required, Validators.min(0), Validators.max(100)]],
    activo: [true],
    variantes: this.fb.array<VariantFormGroup>([], [noDuplicateVariantsValidator]),
  });

  get variantesArray(): FormArray<VariantFormGroup> {
    return this.productForm.controls.variantes;
  }

  ngOnInit(): void {
    this.loadCategories();

    const rawId = this.route.snapshot.paramMap.get('id');
    const parsedId = rawId ? Number(rawId) : NaN;
    if (rawId && Number.isInteger(parsedId) && parsedId > 0) {
      this.productId.set(parsedId);
      this.loadProduct(parsedId);
    } else {
      this.addVariant('M');
    }
  }

  ngOnDestroy(): void {
    for (const item of this.pendingFiles()) {
      URL.revokeObjectURL(item.previewUrl);
    }
  }

  loadCategories(): void {
    this.adminCatalog.getCategories().subscribe({
      next: (cats) => {
        this.categories.set(cats);
        if (this.productId() === null && this.productForm.controls.categoria.value === 0 && cats.length > 0) {
          this.productForm.controls.categoria.setValue(cats[0].id);
        }
      },
      error: () => {
        this.errorMessage.set('No fue posible cargar las categorías disponibles.');
      },
    });
  }

  loadProduct(id: number): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.adminCatalog.getProduct(id).subscribe({
      next: (product) => {
        this.applyLoadedProduct(product);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        this.errorMessage.set(
          err.error?.detail ?? 'No fue posible cargar la información del producto.',
        );
      },
    });
  }

  addVariant(defaultSize: SizeOption = 'M'): void {
    const group: VariantFormGroup = this.fb.group({
      id: new FormControl<number | null>(null),
      talla: this.fb.control<SizeOption>(defaultSize, [Validators.required]),
      color: this.fb.control('', [Validators.required, Validators.maxLength(50)]),
      color_hex: this.fb.control('#1B2A5C', [Validators.required, Validators.pattern(HEX_COLOR_RE)]),
      sku: this.fb.control('', [Validators.maxLength(64)]),
      stock: this.fb.control(0, [Validators.required, Validators.min(0)]),
    });
    this.variantesArray.push(group);
  }

  removeVariant(index: number): void {
    this.variantesArray.removeAt(index);
  }

  isDuplicateRow(index: number): boolean {
    const target = this.variantesArray.at(index);
    const talla = String(target.controls.talla.value ?? '').trim();
    const color = String(target.controls.color.value ?? '').trim().toLowerCase();
    if (!talla || !color) return false;

    let matches = 0;
    for (let i = 0; i < this.variantesArray.length; i++) {
      const row = this.variantesArray.at(i);
      if (
        row.controls.talla.value === talla &&
        row.controls.color.value.trim().toLowerCase() === color
      ) {
        matches++;
      }
    }
    return matches > 1;
  }

  isFieldInvalid(
    name: 'nombre' | 'categoria' | 'precio_base' | 'porcentaje_iva',
  ): boolean {
    const ctrl = this.productForm.controls[name];
    return ctrl.invalid && (ctrl.touched || this.submitted());
  }

  isVariantFieldInvalid(
    index: number,
    name: 'talla' | 'color' | 'color_hex' | 'stock',
  ): boolean {
    const ctrl = this.variantesArray.at(index).controls[name];
    return ctrl.invalid && (ctrl.touched || this.submitted());
  }

  onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.enqueueFiles(Array.from(input.files));
      input.value = '';
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragActive.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.dragActive.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragActive.set(false);
    if (event.dataTransfer?.files?.length) {
      this.enqueueFiles(Array.from(event.dataTransfer.files));
    }
  }

  removePendingFile(id: string): void {
    const current = this.pendingFiles();
    const target = current.find((item) => item.id === id);
    if (target) {
      URL.revokeObjectURL(target.previewUrl);
    }
    this.pendingFiles.set(current.filter((item) => item.id !== id));
  }

  addManualImage(): void {
    this.manualImageError.set(null);
    const raw = this.manualImageInput.value.trim();
    if (!raw) {
      this.manualImageError.set('Ingresa una URL de imagen o un color hexadecimal (#RRGGBB).');
      return;
    }

    const valid =
      HEX_COLOR_RE.test(raw) ||
      raw.startsWith('http://') ||
      raw.startsWith('https://') ||
      raw.startsWith('/media/');

    if (!valid) {
      this.manualImageError.set(
        'Usa una URL válida (http://, https://, /media/...) o un color #RGB / #RRGGBB.',
      );
      return;
    }

    const nextOrder = this.savedImages().length + this.manualImages().length;
    this.manualImages.update((imgs) => [...imgs, { url: raw, orden: nextOrder }]);
    this.manualImageInput.setValue('');
  }

  removeManualImage(index: number): void {
    this.manualImages.update((imgs) => imgs.filter((_, i) => i !== index));
  }

  deleteSavedImage(img: AdminProductImage): void {
    const pid = this.productId();
    if (!pid || !img.id || this.deletingImageId() !== null) return;

    this.deletingImageId.set(img.id);
    this.errorMessage.set(null);

    this.adminCatalog.deleteProductImage(pid, img.id).subscribe({
      next: () => {
        this.deletingImageId.set(null);
        this.savedImages.update((imgs) => imgs.filter((item) => item.id !== img.id));
      },
      error: (err: HttpErrorResponse) => {
        this.deletingImageId.set(null);
        this.errorMessage.set(
          err.error?.detail ?? 'No fue posible eliminar la imagen seleccionada.',
        );
      },
    });
  }

  isImageUrl(url: string): boolean {
    const raw = url.trim();
    return (
      raw.startsWith('http://') ||
      raw.startsWith('https://') ||
      raw.startsWith('/media/') ||
      raw.startsWith('data:') ||
      raw.startsWith('blob:')
    );
  }

  resolveImageSrc(url: string): string {
    const raw = url.trim();
    if (raw.startsWith('/media/')) {
      return `${API_ORIGIN}${raw}`;
    }
    return raw;
  }

  submitProduct(): void {
    this.submitted.set(true);
    this.feedbackMessage.set(null);
    this.errorMessage.set(null);

    if (this.productForm.invalid) {
      this.productForm.markAllAsTouched();
      this.focusFirstInvalid();
      return;
    }

    const raw = this.productForm.getRawValue();
    const nombre = raw.nombre.trim();
    if (!nombre) {
      this.productForm.controls.nombre.setErrors({ required: true });
      this.focusFirstInvalid();
      return;
    }

    const variantes: AdminVariant[] = raw.variantes.map((v) => ({
      ...(v.id !== null ? { id: v.id } : {}),
      talla: v.talla,
      color: v.color.trim(),
      color_hex: v.color_hex.trim() || '#1B2A5C',
      sku: v.sku.trim(),
      stock: Number(v.stock),
    }));

    const keptNonFileSaved = this.savedImages()
      .filter((img) => !img.es_archivo && img.id !== undefined)
      .map((img, idx) => ({ id: img.id, url: img.url, orden: idx }));

    const manualToSave = this.manualImages().map((img, idx) => ({
      url: img.url,
      orden: keptNonFileSaved.length + idx,
    }));

    const payload: AdminProductPayload = {
      nombre,
      descripcion: raw.descripcion.trim(),
      categoria: Number(raw.categoria),
      precio_base: Number(raw.precio_base),
      porcentaje_iva: Number(raw.porcentaje_iva),
      activo: raw.activo,
      variantes,
      imagenes: [...keptNonFileSaved, ...manualToSave],
    };

    const filesToUpload = this.pendingFiles().map((item) => item.file);
    const existingId = this.productId();
    const isCreating = existingId === null;

    this.saving.set(true);

    const save$: Observable<AdminProduct> = isCreating
      ? this.adminCatalog.createProduct(payload)
      : this.adminCatalog.updateProduct(existingId, payload);

    save$
      .pipe(
        switchMap((savedProduct) => {
          this.productId.set(savedProduct.id);
          if (filesToUpload.length === 0) {
            return of({ savedProduct, uploaded: null as AdminProductImage[] | null });
          }
          return this.adminCatalog
            .uploadProductImages(savedProduct.id, filesToUpload)
            .pipe(
              switchMap((uploaded) => of({ savedProduct, uploaded })),
            );
        }),
      )
      .subscribe({
        next: ({ savedProduct, uploaded }) => {
          this.saving.set(false);
          this.clearPendingFiles();
          this.manualImages.set([]);

          const mergedImages = uploaded
            ? [...savedProduct.imagenes, ...uploaded]
            : savedProduct.imagenes;
          this.applyLoadedProduct({ ...savedProduct, imagenes: mergedImages });

          this.feedbackMessage.set(
            isCreating
              ? `Producto "${savedProduct.nombre}" creado correctamente.`
              : `Producto "${savedProduct.nombre}" actualizado correctamente.`,
          );
        },
        error: (err: HttpErrorResponse) => {
          this.saving.set(false);
          if (isCreating && this.productId() !== null) {
            this.errorMessage.set(
              'El producto fue creado, pero falló la subida de imágenes. Reintenta guardar o ajusta los archivos.',
            );
            return;
          }
          this.errorMessage.set(this.extractErrorMessage(err));
        },
      });
  }

  private enqueueFiles(files: File[]): void {
    const errors: string[] = [];
    const validEntries: PendingUploadFile[] = [];

    for (const file of files) {
      if (!ALLOWED_MIME_TYPES.has(file.type)) {
        errors.push(`"${file.name}": formato no permitido (${file.type || 'desconocido'}). Usa JPEG, PNG o WEBP.`);
        continue;
      }
      if (file.size > MAX_IMAGE_BYTES) {
        errors.push(`"${file.name}": supera el máximo de 5 MB (${this.formatBytes(file.size)}).`);
        continue;
      }

      validEntries.push({
        id: `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        file,
        previewUrl: URL.createObjectURL(file),
        name: file.name,
        sizeLabel: this.formatBytes(file.size),
      });
    }

    this.imageErrors.set(errors);
    if (validEntries.length > 0) {
      this.pendingFiles.update((prev) => [...prev, ...validEntries]);
    }
  }

  private clearPendingFiles(): void {
    for (const item of this.pendingFiles()) {
      URL.revokeObjectURL(item.previewUrl);
    }
    this.pendingFiles.set([]);
  }

  private applyLoadedProduct(product: AdminProduct): void {
    this.productForm.patchValue({
      nombre: product.nombre,
      descripcion: product.descripcion,
      categoria: product.categoria,
      precio_base: Number(product.precio_base),
      porcentaje_iva: product.porcentaje_iva,
      activo: product.activo,
    });

    this.variantesArray.clear();
    for (const v of product.variantes) {
      this.variantesArray.push(
        this.fb.group({
          id: new FormControl<number | null>(v.id ?? null),
          talla: this.fb.control<SizeOption>(v.talla, [Validators.required]),
          color: this.fb.control(v.color, [Validators.required, Validators.maxLength(50)]),
          color_hex: this.fb.control(v.color_hex || '#1B2A5C', [
            Validators.required,
            Validators.pattern(HEX_COLOR_RE),
          ]),
          sku: this.fb.control(v.sku ?? '', [Validators.maxLength(64)]),
          stock: this.fb.control(v.stock, [Validators.required, Validators.min(0)]),
        }),
      );
    }

    this.savedImages.set(product.imagenes ?? []);
    this.submitted.set(false);
  }

  private formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  private focusFirstInvalid(): void {
    const el = this.formRef()?.nativeElement.querySelector<HTMLElement>(
      '[aria-invalid="true"], .ng-invalid:not(form):not(fieldset)',
    );
    el?.focus();
  }

  private extractErrorMessage(err: HttpErrorResponse): string {
    const body = err.error;
    if (!body) return 'No se pudo guardar el producto.';
    if (typeof body.detail === 'string') return body.detail;
    if (typeof body === 'string') return body;
    for (const key of ['nombre', 'categoria', 'precio_base', 'porcentaje_iva', 'variantes', 'imagenes']) {
      const val = body[key];
      if (Array.isArray(val) && val[0]) {
        return typeof val[0] === 'string' ? val[0] : JSON.stringify(val[0]);
      }
      if (typeof val === 'string') return val;
    }
    return 'Verifica los datos del formulario e inténtalo de nuevo.';
  }
}
