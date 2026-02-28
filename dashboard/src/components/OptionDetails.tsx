import type {
  Option,
  OptionDetails,
  RebookDetails,
  HotelDetails,
  GroundTransportDetails,
  AltAirportDetails,
  LoungeDetails,
  VoucherDetails,
} from "../types";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function isRebook(d: OptionDetails): d is RebookDetails {
  return "flightNumber" in d && "seatAvailable" in d;
}

function isHotel(d: OptionDetails): d is HotelDetails {
  return "hotelName" in d;
}

function isGround(d: OptionDetails): d is GroundTransportDetails {
  return "route" in d && "provider" in d;
}

function isAltAirport(d: OptionDetails): d is AltAirportDetails {
  return "viaAirport" in d;
}

function isLounge(d: OptionDetails): d is LoungeDetails {
  return "loungeName" in d;
}

function isVoucher(d: OptionDetails): d is VoucherDetails {
  return "voucherType" in d;
}

function RebookInfo({ d }: { d: RebookDetails }) {
  return (
    <span>
      <span className="font-mono font-semibold">{d.flightNumber}</span>
      {" "}
      <span className="text-text-secondary">{d.origin} → {d.destination}</span>
      {" · "}
      <span className="tabular-nums">{formatTime(d.departure)}</span>
      {d.seatAvailable && (
        <span className="ml-1.5 text-accent-green">seat available</span>
      )}
    </span>
  );
}

function HotelInfo({ d }: { d: HotelDetails }) {
  return (
    <span>
      <span className="font-semibold">{d.hotelName}</span>
      {" · "}
      <span className="text-text-secondary">{d.address}</span>
      {d.nextFlightNumber && (
        <>
          {" · next flight "}
          <span className="font-mono">{d.nextFlightNumber}</span>
          {" "}
          <span className="tabular-nums">{formatTime(d.nextFlightDeparture)}</span>
        </>
      )}
    </span>
  );
}

function GroundInfo({ d }: { d: GroundTransportDetails }) {
  const modeLabel: Record<string, string> = { train: "Train", bus: "Bus", taxi: "Taxi" };
  return (
    <span>
      <span className="font-semibold">{modeLabel[d.mode] ?? d.mode}</span>
      {" · "}
      {d.route}
      {" · "}
      <span className="text-text-secondary">{d.provider}</span>
      {" · "}
      <span className="tabular-nums">{formatTime(d.departure)}</span>
      {" → "}
      <span className="tabular-nums">{formatTime(d.arrival)}</span>
    </span>
  );
}

function AltAirportInfo({ d }: { d: AltAirportDetails }) {
  const transferLabel: Record<string, string> = { train: "train", bus: "bus", taxi: "taxi" };
  return (
    <span>
      via <span className="font-mono font-semibold">{d.viaAirport}</span>
      {" on "}
      <span className="font-mono">{d.connectingFlight}</span>
      {" · "}
      {transferLabel[d.transferMode] ?? d.transferMode} transfer
      {" · arr "}
      <span className="tabular-nums">{formatTime(d.totalArrival)}</span>
    </span>
  );
}

function LoungeInfo({ d }: { d: LoungeDetails }) {
  return (
    <span>
      <span className="font-semibold">{d.loungeName}</span>
      {" · "}
      {d.terminal}
      {d.location && <>, {d.location}</>}
      {d.showerAvailable && <> · showers</>}
      {d.sleepingRooms && <> · sleeping rooms</>}
    </span>
  );
}

function VoucherInfo({ d }: { d: VoucherDetails }) {
  return (
    <span>
      <span className="font-semibold">{d.voucherType} voucher</span>
      {" · "}
      <span className="font-mono tabular-nums">{d.amountEur} EUR</span>
      {" · valid until "}
      <span className="tabular-nums">{formatTime(d.validUntil)}</span>
      {d.acceptedAt.length > 0 && (
        <> · {d.acceptedAt.slice(0, 3).join(", ")}{d.acceptedAt.length > 3 ? " +" + (d.acceptedAt.length - 3) + " more" : ""}</>
      )}
    </span>
  );
}

/**
 * Renders structured option details based on the option type.
 * Falls back to the plain description if details are missing or unrecognized.
 */
export function OptionDetailsDisplay({ option }: { option: Option }) {
  const d = option.details;

  if (!d || typeof d !== "object") {
    return <span>{option.description}</span>;
  }

  if (isRebook(d)) return <RebookInfo d={d} />;
  if (isHotel(d)) return <HotelInfo d={d} />;
  if (isGround(d)) return <GroundInfo d={d} />;
  if (isAltAirport(d)) return <AltAirportInfo d={d} />;
  if (isLounge(d)) return <LoungeInfo d={d} />;
  if (isVoucher(d)) return <VoucherInfo d={d} />;

  return <span>{option.description}</span>;
}
