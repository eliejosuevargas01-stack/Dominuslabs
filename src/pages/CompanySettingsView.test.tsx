import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const apiMocks = vi.hoisted(() => ({
  fetchCompanySettings: vi.fn(),
  updateCompanySettings: vi.fn(),
  fetchProducts: vi.fn(),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  deleteProduct: vi.fn(),
  uploadProductMedia: vi.fn(),
  getUserTenant: vi.fn(() => 'tenant-test'),
  resolveApiAssetUrl: vi.fn((assetUrl: string) => `http://api.test${assetUrl}`),
}));

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}));

vi.mock('../services/api', () => apiMocks);
vi.mock('sonner', () => ({ toast: toastMocks }));

import CompanySettingsView from './CompanySettingsView';

describe('CompanySettingsView product media', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getUserTenant.mockReturnValue('tenant-test');
    apiMocks.fetchCompanySettings.mockResolvedValue({
      accepted_payment_types: [],
      delivery_tiers: [],
      promotions: [],
    });
    apiMocks.fetchProducts.mockResolvedValue([]);
    apiMocks.createProduct.mockResolvedValue({
      id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
      name: 'Produto com foto',
      price: 10,
      available: true,
      stock: 1,
    });
    apiMocks.uploadProductMedia.mockResolvedValue({
      media_url: '/uploads/products/prod_test.png',
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('persists a new product before uploading its selected media', async () => {
    const user = userEvent.setup();
    const { container } = render(<CompanySettingsView />);

    await user.click(await screen.findByRole('button', { name: 'Portfólio & Catálogo' }));
    await user.click(screen.getByRole('button', { name: 'Cadastrar Solução' }));
    await user.type(
      screen.getByPlaceholderText('Ex: Licença Plataforma Agente IA Enterprise'),
      'Produto com foto',
    );

    const fileInput = container.querySelector<HTMLInputElement>('input[type="file"]');
    expect(fileInput).not.toBeNull();
    const file = new File(['image bytes'], 'produto.png', { type: 'image/png' });
    await user.upload(fileInput!, file);

    expect(apiMocks.uploadProductMedia).not.toHaveBeenCalled();
    expect(screen.getByText('produto.png')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Homologar Solução' }));

    await waitFor(() => expect(apiMocks.createProduct).toHaveBeenCalledTimes(1));
    expect(apiMocks.createProduct).toHaveBeenCalledWith(
      expect.not.objectContaining({ id: expect.anything() }),
      'tenant-test',
    );
    await waitFor(() => expect(apiMocks.uploadProductMedia).toHaveBeenCalledWith(
      file,
      'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    ));
    expect(apiMocks.createProduct.mock.invocationCallOrder[0])
      .toBeLessThan(apiMocks.uploadProductMedia.mock.invocationCallOrder[0]);
    expect(apiMocks.updateProduct).not.toHaveBeenCalled();
    expect(await screen.findByRole('img', { name: 'Produto com foto' }))
      .toHaveAttribute('src', 'http://api.test/uploads/products/prod_test.png');
  });

  it('renders products list with BRL currency formatting, category badge, and fallback icon when no media', async () => {
    apiMocks.fetchProducts.mockResolvedValue([
      {
        id: 'prod-1',
        name: 'Plataforma Omnichannel',
        category: 'Software',
        price: 1490.50,
        available: true,
        stock: 5,
        description: 'Solução completa para atendimento multicanal.',
      },
    ]);

    const user = userEvent.setup();
    render(<CompanySettingsView />);

    await user.click(await screen.findByRole('button', { name: 'Portfólio & Catálogo' }));

    expect(await screen.findByText('Plataforma Omnichannel')).toBeInTheDocument();
    
    // Monetary formatting check
    const priceElement = screen.getByText('R$ 1.490,50');
    expect(priceElement).toBeInTheDocument();
    expect(priceElement).toHaveClass('font-bold', 'text-emerald-700', 'bg-emerald-50');

    // Category badge check
    const categoryBadge = screen.getByText('Software');
    expect(categoryBadge).toBeInTheDocument();
    expect(categoryBadge).toHaveClass('text-zinc-500', 'bg-zinc-100');

    // Fallback icon package when no media
    expect(screen.queryByRole('img', { name: 'Plataforma Omnichannel' })).not.toBeInTheDocument();
  });
});

