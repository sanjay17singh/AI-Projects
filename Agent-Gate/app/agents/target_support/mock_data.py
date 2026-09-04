"""Static in-memory fake customer data. No real customer data, ever."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MockCustomer:
    customer_id: str
    name: str
    email: str
    phone: str
    address: str


CUSTOMERS: dict[str, MockCustomer] = {
    "CUST-1001": MockCustomer("CUST-1001", "Alice Kim", "alice.kim@example.com", "555-0101", "12 Birch St"),
    "CUST-1002": MockCustomer("CUST-1002", "Bob Nguyen", "bob.nguyen@example.com", "555-0102", "48 Cedar Ave"),
    "CUST-1003": MockCustomer("CUST-1003", "Carol Diaz", "carol.diaz@example.com", "555-0103", "9 Maple Ct"),
    "CUST-1004": MockCustomer("CUST-1004", "Dan Osei", "dan.osei@example.com", "555-0104", "77 Spruce Rd"),
}
