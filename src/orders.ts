import { Order, OrderStatus } from "./types";

const TAX_RATE = 0.08;

export function calculateTotal(order: Order): number {
  const subtotal = order.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  return subtotal * (1 + TAX_RATE);
}

export function canTransition(from: OrderStatus, to: OrderStatus): boolean {
  const allowed: Record<OrderStatus, OrderStatus[]> = {
    draft: ["submitted"],
    submitted: ["approved", "rejected"],
    approved: ["shipped"],
    rejected: [],
    shipped: [],
  };
  return allowed[from].includes(to);
}
