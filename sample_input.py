class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_item(self, name: str, price: float):
        if price < 0:
            raise ValueError("Price cannot be negative")
        self.items.append({"name": name, "price": price})

    def total(self) -> float:
        return sum(item["price"] for item in self.items)


def apply_discount(amount: float, percentage: float) -> float:
    if not 0 <= percentage <= 100:
        raise ValueError("Discount must be between 0 and 100")
    return amount * (1 - percentage / 100)


def main():
    cart = ShoppingCart()
    cart.add_item("Notebook", 50.0)
    cart.add_item("Pen", 10.0)
    print(f"Cart total: {cart.total():.2f}")
    print(f"Discounted total: {apply_discount(cart.total(), 10):.2f}")


if __name__ == "__main__":
    main()
