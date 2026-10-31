const SYMBOLS = { CRC: "₡", USD: "$" };

export const CURRENCIES = [
  { value: "CRC", label: "₡ Colones" },
  { value: "USD", label: "$ Dólares" },
];

export function formatMoney(value, currency = "CRC") {
  return `${SYMBOLS[currency] ?? SYMBOLS.CRC}${Number(value ?? 0).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
