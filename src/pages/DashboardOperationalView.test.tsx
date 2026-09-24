import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';

import DashboardOperationalView from './DashboardOperationalView';

// Mock the API module so fetchOperationalDashboard is controllable in tests
vi.mock('../services/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('../services/api')>();
  return {
    ...original,
    fetchOperationalDashboard: vi.fn().mockResolvedValue({
      metrics: { pedidosHoje: 0, ticketMedio: 0, faturamentoDia: 0, taxaConversao: 0 },
      efficiency: { atendimentosIa: 0, atendimentosHumanos: 0, porcentagemIa: 0 },
      orders: [],
    }),
  };
});

const todayISO = new Date().toISOString();

const baseMetrics = {
  pedidosHoje: 2,
  ticketMedio: 100.00,
  faturamentoDia: 200.00,
  taxaConversao: 50.0,
};

const baseEfficiency = {
  atendimentosIa: 14,
  atendimentosHumanos: 2,
  porcentagemIa: 88,
};

const fakeOrders = [
  {
    id: 'ord-12345678',
    clienteNome: 'Maria Silva',
    valorTotal: 150.00,
    status: 'CONCLUIDO' as const,
    tempoAtendimento: '5 min',
    horaPedido: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
  },
  {
    id: 'ord-87654321',
    clienteNome: 'João Santos',
    valorTotal: 50.00,
    status: 'NOVO' as const,
    tempoAtendimento: '5 min',
    horaPedido: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
  },
];

describe('DashboardOperationalView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders metrics when provided via props', () => {
    render(<DashboardOperationalView metrics={baseMetrics} efficiency={baseEfficiency} orders={fakeOrders} />);

    // Check KPI displayed from props - use card queries for specificity
    const pedidosHojeCard = screen.getByText('Pedidos Hoje').closest('.surface-card');
    expect(pedidosHojeCard).toHaveTextContent('2');

    expect(screen.getByText('R$ 100,00')).toBeInTheDocument(); // ticketMedio
    expect(screen.getByText('R$ 200,00')).toBeInTheDocument(); // faturamentoDia
    expect(screen.getByText('50.0%')).toBeInTheDocument(); // taxaConversao
  });

  it('renders empty queue state when no orders provided', () => {
    render(<DashboardOperationalView metrics={baseMetrics} efficiency={baseEfficiency} orders={[]} />);

    expect(screen.getByText('Nenhum pedido mapeado na sessão atual.')).toBeInTheDocument();
  });

  it('calls onRefresh callback when refresh button is clicked', async () => {
    const onRefreshMock = vi.fn();
    render(<DashboardOperationalView metrics={baseMetrics} efficiency={baseEfficiency} orders={fakeOrders} onRefresh={onRefreshMock} />);

    // Wait for initial fetch to complete so button is enabled
    await waitFor(() => {
      const refreshBtn = screen.getByTitle('Atualizar Dados Operacionais');
      expect(refreshBtn).not.toBeDisabled();
    });

    const refreshBtn = screen.getByTitle('Atualizar Dados Operacionais');
    act(() => {
      fireEvent.click(refreshBtn);
    });

    expect(onRefreshMock).toHaveBeenCalledTimes(1);
  });

  it('displays loading state when loading prop is true', () => {
    render(
      <DashboardOperationalView
        metrics={baseMetrics}
        efficiency={baseEfficiency}
        orders={fakeOrders}
        loading={true}
      />
    );

    // Refresh button should be disabled
    const refreshBtn = screen.getByTitle('Atualizar Dados Operacionais');
    expect(refreshBtn).toBeDisabled();
  });
});
