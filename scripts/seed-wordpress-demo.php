<?php
// Demo content for screenshots: an invented community-garden journal.
// Images are Twenty Twenty-Five's own bundled photos (GPL, shipped in core).
// Usage, in the app pod as www-data:
//   setpriv --reuid=www-data --regid=www-data --init-groups php seed-wordpress-demo.php [seed|dark|light]
// "dark" applies Twenty Twenty-Five's Evening style variation for dark screenshots; "light" resets it.
$_SERVER['HTTP_HOST'] = parse_url(getenv('WORDPRESS_SITE_URL'), PHP_URL_HOST);
$_SERVER['HTTPS'] = 'on';
define('WP_USE_THEMES', false);
require '/var/www/html/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/media.php';
wp_set_current_user(1);
$mode = $argv[1] ?? 'seed';

function style_variation($slug) {
    $id = WP_Theme_JSON_Resolver::get_user_global_styles_post_id();
    $data = array('version' => 3, 'isGlobalStylesUserThemeJSON' => true);
    if ($slug) {
        $v = json_decode(file_get_contents(get_template_directory() . "/styles/$slug.json"), true);
        foreach (array('settings', 'styles') as $k) if (isset($v[$k])) $data[$k] = $v[$k];
        $data['title'] = $v['title'] ?? $slug;
    }
    wp_update_post(array('ID' => $id, 'post_content' => wp_json_encode($data)));
    delete_transient('global_styles'); wp_clean_theme_json_cache();
    echo "style: " . ($slug ?: 'default') . "\n";
}
if ($mode === 'dark') { style_variation('01-evening'); exit; }
if ($mode === 'light') { style_variation(''); exit; }

update_option('blogname', 'Fernhill Garden Journal');
update_option('blogdescription', 'Notes from a small community garden');
wp_update_user(array('ID' => 1, 'first_name' => 'Mara', 'last_name' => 'Ellis', 'display_name' => 'Mara Ellis', 'nickname' => 'Mara'));
// Drop the sample content.
foreach (array(1 => 'post', 2 => 'page', 3 => 'page') as $id => $t) wp_delete_post($id, true);
foreach (get_posts(array('post_type' => 'post', 'numberposts' => -1, 'post_status' => 'any')) as $p) wp_delete_post($p->ID, true);
foreach (get_posts(array('post_type' => 'attachment', 'numberposts' => -1, 'post_status' => 'any')) as $p) wp_delete_attachment($p->ID, true);
foreach (get_posts(array('post_type' => 'page', 'numberposts' => -1, 'post_status' => 'any')) as $p) wp_delete_post($p->ID, true);
foreach (get_users(array('login' => 'qa-mail')) as $u) { require_once ABSPATH . 'wp-admin/includes/user.php'; wp_delete_user($u->ID, 1); }

$img = get_template_directory() . '/assets/images/';
function attach($file, $alt) {
    $tmp = wp_tempnam($file); copy($file, $tmp);
    $id = media_handle_sideload(array('name' => basename($file), 'tmp_name' => $tmp), 0);
    if (is_wp_error($id)) { echo 'media error: ' . $id->get_error_message() . "\n"; return 0; }
    update_post_meta($id, '_wp_attachment_image_alt', $alt);
    return $id;
}
function para($t) { return "<!-- wp:paragraph -->\n<p>$t</p>\n<!-- /wp:paragraph -->\n\n"; }
function head($t) { return "<!-- wp:heading -->\n<h2 class=\"wp-block-heading\">$t</h2>\n<!-- /wp:heading -->\n\n"; }
function cat($name) { $t = term_exists($name, 'category') ?: wp_insert_term($name, 'category'); return (int) $t['term_id']; }

$posts = array(
    array('Planting delphiniums for a summer of blue', 'delphinium-flowers.webp', 'Tall blue delphinium spikes', 'Flowers', -2,
        para('Every spring someone asks how we get the back border to turn that shade of blue in July. The answer is patience, a sunny spot and a little support.') .
        head('Start with good soil') . para('Delphiniums want rich, well drained soil. We dig in a barrow of compost per square metre in March and keep the crowns just at soil level.') .
        head('Stake early') . para('Put the canes in when the shoots are a hand high. By the time the spikes are heavy with flowers it is too late, and one summer storm will flatten the lot.') .
        para('Deadhead the first flush and you will often get a second, shorter show in September.')),
    array('Five sunflower varieties worth growing', 'category-sunflowers.webp', 'Sunflowers in a field', 'Flowers', -5,
        para('We trialled eleven sunflowers along the south fence this year. These five earned a place again next season, from the six foot giants to a bushy dwarf for the children\'s bed.') .
        head('Our favourites') . para('Russian Giant for height, Velvet Queen for its deep red, Italian White for cutting, Teddy Bear for containers and Valentine for the bees.')),
    array('A morning walk through the marsh', 'marshland-birds-square.webp', 'Birds over a marsh at dawn', 'Wildlife', -9,
        para('The wet meadow at the bottom of the plot is the least tidy corner we have, and the busiest. At six in the morning it is all wings.') .
        para('We counted herons, two kinds of warbler and a family of moorhens. Leave a wild margin and the wildlife will find it.')),
    array('Caring for anthuriums indoors', 'category-anthuriums.webp', 'Red anthurium flowers', 'Houseplants', -14,
        para('Our winter workshop on houseplants filled up in a day, so here are the notes. Anthuriums like bright, indirect light, warm rooms and a chunky, airy potting mix.') .
        head('Watering') . para('Let the top few centimetres dry out between waterings. Yellow leaves almost always mean too much water, not too little.')),
    array('Why we leave the meadow unmown', 'flower-meadow-square.webp', 'Wildflower meadow in summer', 'Wildlife', -21,
        para('Visitors sometimes think we forgot to cut the grass by the gate. We did not. The strip is a meadow now, and it flowers from May to October.') .
        para('We cut it once, in late summer, and take the hay away so the soil stays poor. Poor soil means more flowers and fewer thistles.')),
    array('Notes on red hibiscus', 'red-hibiscus-closeup.webp', 'Close up of a red hibiscus flower', 'Houseplants', -30,
        para('The hibiscus in the greenhouse has flowered non stop since June. Feed it every week in summer, keep it out of draughts and bring it in before the first frost.')),
);
$first = 0;
foreach ($posts as $p) {
    list($title, $file, $alt, $c, $days, $body) = $p;
    $mid = attach($img . $file, $alt);
    $html = $body;
    $date = gmdate('Y-m-d H:i:s', time() + $days * 86400);
    $id = wp_insert_post(array('post_title' => $title, 'post_content' => $html, 'post_status' => 'publish', 'post_author' => 1,
        'post_category' => array(cat($c)), 'post_date_gmt' => $date, 'post_date' => get_date_from_gmt($date)));
    if ($mid) { set_post_thumbnail($id, $mid); wp_update_post(array('ID' => $mid, 'post_parent' => $id)); }
    $first = $first ?: $id;
    echo "post $id: $title\n";
}
wp_delete_term(1, 'category'); // Uncategorized
foreach (array('About' => para('Fernhill is a community garden run by volunteers on an old allotment site. We grow food, flowers and habitat, and we write about it here.'),
               'Visit' => para('The garden is open to everyone on Saturday mornings from nine until noon. Bring gloves if you want to help.')) as $t => $c) {
    $id = wp_insert_post(array('post_title' => $t, 'post_content' => $c, 'post_status' => 'publish', 'post_type' => 'page'));
    echo "page $id: $t\n";
}
// Front page built from core blocks: a cover hero and a grid of the latest posts.
$hero = attach($img . 'flower-meadow-square.webp', 'Wildflower meadow');
$hurl = wp_get_attachment_image_url($hero, 'full');
$front = <<<HTML
<!-- wp:cover {"url":"$hurl","id":$hero,"dimRatio":40,"minHeight":520,"align":"full","layout":{"type":"constrained"}} -->
<div class="wp-block-cover alignfull" style="min-height:520px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim-40 has-background-dim"></span><img class="wp-block-cover__image-background wp-image-$hero" alt="" src="$hurl" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":1,"fontSize":"xx-large"} -->
<h1 class="wp-block-heading has-text-align-center has-xx-large-font-size">Grow something together</h1>
<!-- /wp:heading -->

<!-- wp:paragraph {"align":"center","fontSize":"large"} -->
<p class="has-text-align-center has-large-font-size">Notes, seasons and open days from the Fernhill community garden.</p>
<!-- /wp:paragraph --></div></div>
<!-- /wp:cover -->

<!-- wp:group {"align":"wide","layout":{"type":"constrained","contentSize":"1200px"}} -->
<div class="wp-block-group alignwide"><!-- wp:heading {"fontSize":"x-large"} -->
<h2 class="wp-block-heading has-x-large-font-size">From the journal</h2>
<!-- /wp:heading -->

<!-- wp:query {"queryId":1,"query":{"perPage":6,"postType":"post","order":"desc","orderBy":"date","inherit":false},"align":"wide"} -->
<div class="wp-block-query alignwide"><!-- wp:post-template {"layout":{"type":"grid","columnCount":3}} -->
<!-- wp:post-featured-image {"isLink":true,"aspectRatio":"3/2"} /-->
<!-- wp:post-title {"isLink":true,"fontSize":"large"} /-->
<!-- wp:post-date {"fontSize":"small"} /-->
<!-- /wp:post-template --></div>
<!-- /wp:query --></div>
<!-- /wp:group -->
HTML;
$home = wp_insert_post(array('post_title' => 'Home', 'post_content' => $front, 'post_status' => 'publish', 'post_type' => 'page'));
update_post_meta($home, '_wp_page_template', 'page-no-title');
update_option('show_on_front', 'page'); update_option('page_on_front', $home);
foreach (array('Home' => 0, 'About' => 1, 'Visit' => 2) as $t => $o) { $pg = get_page_by_title($t); if ($pg) wp_update_post(array('ID' => $pg->ID, 'menu_order' => $o)); }
echo "front page $home\n";
// A draft for the editor shot.
$mid = attach($img . 'botany-flowers.webp', 'Spring flowers on the potting bench');
$url = $mid ? wp_get_attachment_image_url($mid, 'large') : '';
$draft = wp_insert_post(array('post_title' => 'Seed swap this Saturday', 'post_status' => 'draft', 'post_author' => 1, 'post_category' => array(cat('News')),
    'post_content' => para('Our spring seed swap is back. Bring packets you saved last autumn, take home something new, and stay for tea in the potting shed.') .
        ($mid ? "<!-- wp:image {\"id\":$mid,\"sizeSlug\":\"large\"} -->\n<figure class=\"wp-block-image size-large\"><img src=\"$url\" alt=\"Spring flowers on the potting bench\" class=\"wp-image-$mid\"/></figure>\n<!-- /wp:image -->\n\n" : '') .
        head('What to bring') . para('Labelled seed packets, a pen and a bag to carry your new seeds home. Tomatoes, beans and annual flowers are always popular.')));
if ($mid) set_post_thumbnail($draft, $mid);
echo "draft $draft\n";
// Quieter dashboard: no welcome panel or editor tips for the admin.
update_user_meta(1, 'show_welcome_panel', 0);
update_user_meta(1, 'wp_persisted_preferences', array('core' => array('isComplementaryAreaVisible' => true, 'welcomeGuide' => false, 'enableChoosePatternModal' => false), 'core/edit-post' => array('welcomeGuide' => false, 'fullscreenMode' => true), '_modified' => gmdate('c')));
echo "seeded\n";
