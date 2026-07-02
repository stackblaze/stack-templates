<?php

use App\Models\Event;
use App\Models\Organiser;
use App\Models\Ticket;
use App\Models\User;
use Carbon\Carbon;
use Illuminate\Database\Seeder;
use Illuminate\Support\Str;

class DemoSeeder extends Seeder
{
    public function run()
    {
        Eloquent::unguard();

        $user = User::orderBy('id')->first();
        if (!$user) {
            echo "DemoSeeder: no admin user found, skipping\n";
            return;
        }

        if (Organiser::where('account_id', $user->account_id)->exists()) {
            echo "DemoSeeder: demo data already present, skipping\n";
            return;
        }

        $accountId = $user->account_id;
        $userId = $user->id;
        $email = $user->email;
        $currencyId = config('attendize.default_currency');
        $dateFormat = config('attendize.default_datetime_format');

        $organiser = Organiser::create([
            'account_id' => $accountId,
            'name' => 'StackBlaze Demo Events',
            'about' => 'Sample organiser created automatically on deploy. Edit or replace this profile after login.',
            'email' => $email,
            'phone' => '',
            'confirmation_key' => Str::random(20),
            'facebook' => '',
            'twitter' => '',
            'is_email_confirmed' => 1,
        ]);

        $events = [
            [
                'title' => 'Sample Conference 2026',
                'description' => 'A demo conference event with free and paid tickets. Explore Attendize features after logging in.',
                'venue_name' => 'Demo Convention Center',
                'location_address_line_1' => '100 Demo Street',
                'location_address_line_2' => '',
                'location_state' => 'NY',
                'location_post_code' => '10001',
                'start' => Carbon::now()->addDays(30),
                'end' => Carbon::now()->addDays(30)->addHours(8),
                'tickets' => [
                    ['title' => 'General Admission', 'price' => 0, 'qty' => 100],
                    ['title' => 'VIP Pass', 'price' => 49.00, 'qty' => 25],
                ],
            ],
            [
                'title' => 'Community Workshop',
                'description' => 'Hands-on workshop with sample ticket types for testing checkout flows.',
                'venue_name' => 'StackBlaze Community Hall',
                'location_address_line_1' => '200 Workshop Ave',
                'location_address_line_2' => 'Suite 5',
                'location_state' => 'CA',
                'location_post_code' => '94105',
                'start' => Carbon::now()->addDays(45),
                'end' => Carbon::now()->addDays(45)->addHours(3),
                'tickets' => [
                    ['title' => 'Workshop Seat', 'price' => 15.00, 'qty' => 50],
                    ['title' => 'Early Bird', 'price' => 10.00, 'qty' => 20],
                ],
            ],
        ];

        foreach ($events as $spec) {
            $event = Event::create([
                'title' => $spec['title'],
                'description' => $spec['description'],
                'venue_name' => $spec['venue_name'],
                'venue_name_full' => $spec['venue_name'],
                'location_address_line_1' => $spec['location_address_line_1'],
                'location_address_line_2' => $spec['location_address_line_2'],
                'location_state' => $spec['location_state'],
                'location_post_code' => $spec['location_post_code'],
                'start_date' => $spec['start']->format($dateFormat),
                'end_date' => $spec['end']->format($dateFormat),
                'on_sale_date' => Carbon::now()->format($dateFormat),
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
                    'start_sale_date' => Carbon::now()->format($dateFormat),
                    'end_sale_date' => $spec['end']->format($dateFormat),
                ]);
            }
        }

        echo "DemoSeeder: created organiser and sample events\n";
    }
}
