export type OrderStatus = "draft" | "submitted" | "approved" | "rejected" | "shipped";

export interface OrderItem {
  sku: string;
  price: number;
  quantity: number;
}

export interface Order {
  id: string;
  status: OrderStatus;
  items: OrderItem[];
}
