<?php

use App\Models\Attendee;
use App\Models\Event;
use App\Models\EventStats;
use App\Models\Order;
use App\Models\OrderItem;
use App\Models\Organiser;
use App\Models\Ticket;
use App\Models\User;
use Carbon\Carbon;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Populate Attendize with realistic demo analytics after first boot:
 * orders, attendees, ticket sales, event_stats (charts), and extra calendar events.
 *
 * Safe to re-run: skips when demo orders already exist.
 * Run inside the web container:
 *   php artisan db:seed --class=DemoAnalyticsSeeder --force
 */
class DemoAnalyticsSeeder extends Seeder
{
    private const MARKER = 'stackblaze-demo-analytics';

    /** @var array<int, array{first:string,last:string,email:string}> */
    private $buyers = [
        ['first' => 'Alex', 'last' => 'Morgan', 'email' => 'alex.morgan@demo.stackblaze.app'],
        ['first' => 'Jordan', 'last' => 'Lee', 'email' => 'jordan.lee@demo.stackblaze.app'],
        ['first' => 'Sam', 'last' => 'Patel', 'email' => 'sam.patel@demo.stackblaze.app'],
        ['first' => 'Taylor', 'last' => 'Brooks', 'email' => 'taylor.brooks@demo.stackblaze.app'],
        ['first' => 'Casey', 'last' => 'Nguyen', 'email' => 'casey.nguyen@demo.stackblaze.app'],
        ['first' => 'Riley', 'last' => 'Chen', 'email' => 'riley.chen@demo.stackblaze.app'],
        ['first' => 'Morgan', 'last' => 'Diaz', 'email' => 'morgan.diaz@demo.stackblaze.app'],
        ['first' => 'Jamie', 'last' => 'Okafor', 'email' => 'jamie.okafor@demo.stackblaze.app'],
        ['first' => 'Drew', 'last' => 'Kowalski', 'email' => 'drew.kowalski@demo.stackblaze.app'],
        ['first' => 'Quinn', 'last' => 'Andersson', 'email' => 'quinn.andersson@demo.stackblaze.app'],
    ];

    public function run()
    {
        Model::unguard();

        if (Order::where('notes', self::MARKER)->exists()) {
            echo "DemoAnalyticsSeeder: demo orders already present, skipping\n";
            return;
        }

        $user = User::orderBy('id')->first();
        if (!$user) {
            echo "DemoAnalyticsSeeder: no user found, skipping\n";
            return;
        }

        $organiser = Organiser::where('account_id', $user->account_id)->first();
        if (!$organiser) {
            echo "DemoAnalyticsSeeder: no organiser found, skipping\n";
            return;
        }

        $dateFormat = config('attendize.default_datetime_format');
        $currencyId = config('attendize.default_currency');
        $accountId = $user->account_id;
        $userId = $user->id;

        $this->seedCalendarEvents($organiser, $accountId, $userId, $currencyId, $dateFormat);

        $events = Event::where('organiser_id', $organiser->id)->get();
        if ($events->isEmpty()) {
            echo "DemoAnalyticsSeeder: no events found, skipping\n";
            return;
        }

        $buyerIndex = 0;
        foreach ($events as $event) {
            $tickets = Ticket::where('event_id', $event->id)->get();
            if ($tickets->isEmpty()) {
                continue;
            }

            $primary = $tickets->first();
            $ordersForEvent = $event->id % 2 === 0 ? 5 : 4;

            for ($i = 0; $i < $ordersForEvent; $i++) {
                $ticket = $tickets[$i % $tickets->count()];
                $qty = ($i % 3) + 1;
                $buyer = $this->buyers[$buyerIndex % count($this->buyers)];
                $buyerIndex++;

                $daysAgo = 19 - (($i * 3 + $event->id) % 20);
                $orderedAt = Carbon::now()->subDays($daysAgo)->setTime(10 + ($i % 8), ($i * 7) % 60);

                $this->createOrderBundle(
                    $event,
                    $ticket,
                    $accountId,
                    $buyer,
                    $qty,
                    $orderedAt
                );
            }

            $this->backfillEventStats($event);
            $this->syncEventTotals($event);
        }

        echo "DemoAnalyticsSeeder: seeded analytics for {$events->count()} event(s)\n";
    }

    private function seedCalendarEvents(
        Organiser $organiser,
        int $accountId,
        int $userId,
        $currencyId,
        string $dateFormat
    ): void {
        $calendarEvents = [
            [
                'title' => 'Product Launch Night',
                'venue' => 'StackBlaze HQ',
                'city' => '100 Innovation Way',
                'state' => 'CA',
                'post' => '94105',
                'start' => Carbon::create(2026, 7, 3, 18, 0),
                'end' => Carbon::create(2026, 7, 3, 21, 0),
                'tickets' => [
                    ['title' => 'General Admission', 'price' => 0, 'qty' => 120],
                    ['title' => 'VIP Lounge', 'price' => 35.00, 'qty' => 30],
                ],
            ],
            [
                'title' => 'Founder Fireside',
                'venue' => 'Harbor View Studio',
                'city' => '22 Pier Street',
                'state' => 'NY',
                'post' => '10001',
                'start' => Carbon::create(2026, 7, 12, 17, 30),
                'end' => Carbon::create(2026, 7, 12, 19, 30),
                'tickets' => [
                    ['title' => 'Seat', 'price' => 12.00, 'qty' => 60],
                ],
            ],
            [
                'title' => 'Design Systems Meetup',
                'venue' => 'Creative Hub',
                'city' => '48 Market Street',
                'state' => 'CA',
                'post' => '94103',
                'start' => Carbon::create(2026, 7, 18, 18, 0),
                'end' => Carbon::create(2026, 7, 18, 20, 0),
                'tickets' => [
                    ['title' => 'Meetup Pass', 'price' => 8.00, 'qty' => 80],
                ],
            ],
            [
                'title' => 'Summer Tech Social',
                'venue' => 'Rooftop Terrace',
                'city' => '5 Skyline Ave',
                'state' => 'TX',
                'post' => '73301',
                'start' => Carbon::create(2026, 7, 26, 19, 0),
                'end' => Carbon::create(2026, 7, 26, 22, 0),
                'tickets' => [
                    ['title' => 'Social Ticket', 'price' => 18.00, 'qty' => 100],
                    ['title' => 'Plus One', 'price' => 12.00, 'qty' => 50],
                ],
            ],
            [
                'title' => 'Kubernetes Clinic',
                'venue' => 'Cloud Campus',
                'city' => '300 Cluster Lane',
                'state' => 'WA',
                'post' => '98101',
                'start' => Carbon::create(2026, 8, 2, 9, 0),
                'end' => Carbon::create(2026, 8, 2, 16, 0),
                'tickets' => [
                    ['title' => 'Workshop Seat', 'price' => 49.00, 'qty' => 40],
                ],
            ],
            [
                'title' => 'Open Source Summit',
                'venue' => 'Convention Hall B',
                'city' => '900 Expo Drive',
                'state' => 'IL',
                'post' => '60601',
                'start' => Carbon::create(2026, 8, 16, 9, 0),
                'end' => Carbon::create(2026, 8, 16, 18, 0),
                'tickets' => [
                    ['title' => 'Day Pass', 'price' => 79.00, 'qty' => 200],
                    ['title' => 'Student', 'price' => 25.00, 'qty' => 75],
                ],
            ],
        ];

        foreach ($calendarEvents as $spec) {
            if (Event::where('organiser_id', $organiser->id)->where('title', $spec['title'])->exists()) {
                continue;
            }

            $event = Event::create([
                'title' => $spec['title'],
                'description' => 'Demo calendar event for Stackblaze showcase.',
                'venue_name' => $spec['venue'],
                'venue_name_full' => $spec['venue'],
                'location_address_line_1' => $spec['city'],
                'location_address_line_2' => '',
                'location_state' => $spec['state'],
                'location_post_code' => $spec['post'],
                'start_date' => $spec['start']->format($dateFormat),
                'end_date' => $spec['end']->format($dateFormat),
                'on_sale_date' => Carbon::now()->subDays(7)->format($dateFormat),
                'account_id' => $accountId,
                'user_id' => $userId,
                'currency_id' => $currencyId,
                'organiser_id' => $organiser->id,
                'is_live' => true,
            ]);

            foreach ($spec['tickets'] as $ticketSpec) {
                Ticket::create([
                    'event_id' => $event->id,
                    'account_id' => $accountId,
                    'user_id' => $userId,
                    'title' => $ticketSpec['title'],
                    'description' => 'Demo ticket type',
                    'price' => $ticketSpec['price'],
                    'quantity_available' => $ticketSpec['qty'],
                    'start_sale_date' => Carbon::now()->subDays(7)->format($dateFormat),
                    'end_sale_date' => $spec['end']->format($dateFormat),
                ]);
            }
        }
    }

    private function createOrderBundle(
        Event $event,
        Ticket $ticket,
        int $accountId,
        array $buyer,
        int $qty,
        Carbon $orderedAt
    ): void {
        $lineTotal = round((float) $ticket->price * $qty, 2);

        $order = Order::create([
            'first_name' => $buyer['first'],
            'last_name' => $buyer['last'],
            'email' => $buyer['email'],
            'order_status_id' => 1,
            'amount' => $lineTotal,
            'account_id' => $accountId,
            'event_id' => $event->id,
            'taxamt' => 0,
            'booking_fee' => 0,
            'organiser_booking_fee' => 0,
            'order_date' => $orderedAt->format('Y-m-d'),
            'notes' => self::MARKER,
            'created_at' => $orderedAt,
            'updated_at' => $orderedAt,
        ]);

        $order->tickets()->attach($ticket->id);

        OrderItem::create([
            'title' => $ticket->title,
            'quantity' => $qty,
            'unit_price' => $ticket->price,
            'unit_booking_fee' => 0,
            'order_id' => $order->id,
        ]);

        for ($n = 1; $n <= $qty; $n++) {
            Attendee::create([
                'order_id' => $order->id,
                'event_id' => $event->id,
                'ticket_id' => $ticket->id,
                'account_id' => $accountId,
                'first_name' => $buyer['first'],
                'last_name' => $buyer['last'] . ($qty > 1 ? " {$n}" : ''),
                'email' => $buyer['email'],
                'reference_index' => $n,
                'created_at' => $orderedAt,
                'updated_at' => $orderedAt,
            ]);
        }

        $ticket->quantity_sold = (int) $ticket->quantity_sold + $qty;
        $ticket->sales_volume = round((float) $ticket->sales_volume + $lineTotal, 2);
        $ticket->save();

        EventStats::updateOrCreate(
            [
                'event_id' => $event->id,
                'date' => $orderedAt->format('Y-m-d'),
            ],
            [
                'views' => 0,
                'unique_views' => 0,
                'tickets_sold' => 0,
                'sales_volume' => 0,
                'organiser_fees_volume' => 0,
            ]
        );

        DB::table('event_stats')
            ->where('event_id', $event->id)
            ->where('date', $orderedAt->format('Y-m-d'))
            ->update([
                'tickets_sold' => DB::raw('tickets_sold + ' . (int) $qty),
                'sales_volume' => DB::raw('sales_volume + ' . (float) $lineTotal),
                'views' => DB::raw('views + ' . (int) (12 + ($qty * 3))),
                'unique_views' => DB::raw('unique_views + ' . (int) (5 + $qty)),
            ]);
    }

    private function backfillEventStats(Event $event): void
    {
        for ($daysAgo = 19; $daysAgo >= 0; $daysAgo--) {
            $date = Carbon::now()->subDays($daysAgo)->format('Y-m-d');
            $existing = EventStats::where('event_id', $event->id)->where('date', $date)->first();
            if ($existing) {
                continue;
            }

            $noise = ($event->id + $daysAgo) % 7;
            EventStats::create([
                'event_id' => $event->id,
                'date' => $date,
                'views' => 8 + $noise * 2,
                'unique_views' => 3 + $noise,
                'tickets_sold' => 0,
                'sales_volume' => 0,
                'organiser_fees_volume' => 0,
            ]);
        }
    }

    private function syncEventTotals(Event $event): void
    {
        $ticketSold = Ticket::where('event_id', $event->id)->sum('quantity_sold');
        $salesVolume = Ticket::where('event_id', $event->id)->sum('sales_volume');

        $viewTotal = EventStats::where('event_id', $event->id)->sum('views');
        if ($viewTotal < 40) {
            $boost = 40 - $viewTotal;
            $stat = EventStats::where('event_id', $event->id)->orderBy('date', 'desc')->first();
            if ($stat) {
                $stat->views += $boost;
                $stat->unique_views += (int) ceil($boost / 3);
                $stat->save();
            }
        }

        echo "  event #{$event->id} {$event->title}: {$ticketSold} tickets, €{$salesVolume} revenue\n";
    }
}
