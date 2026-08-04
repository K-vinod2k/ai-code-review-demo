import { Order } from "./types";

export async function fetchDiscount(code: string): Promise<number> {
  const res = await fetch(`https://api.example.com/discounts/${code}`);
  const data = await res.json();
  return data.percentOff;
}

export async function applyDiscount(order: Order, code: string): Promise<number> {
  const subtotal = order.items.reduce((sum, i) => sum + i.price * i.quantity, 0);
  const percentOff = await fetchDiscount(code);
  return subtotal - subtotal * (percentOff / 100);
}
