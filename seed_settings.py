"""Seed script to populate default SiteSetting values."""
from app import create_app, db
from app.models import SiteSetting

DEFAULT_SETTINGS = {
    # Brand & Navbar
    'brand_name': 'Griya Rias Saraswati',
    'brand_tagline': 'Beauty, Elegance, and Wedding Needs All in One Place.',
    'logo_path': '',

    # Hero Section
    'hero_title': 'Griya Rias Saraswati',
    'hero_subtitle': '"Beauty, Elegance, and Wedding Needs All in One Place."',
    'hero_bg_path': 'images/wedding_hero.png',

    # Why Choose Us
    'why_choose_us_p1': 'Kami percaya bahwa setiap pernikahan memiliki cerita istimewa. Melalui layanan rias professional dan penyewaan peralatan pernikahan, kami hadir untuk mempercantik setiap momen berharga di hari bahagia Anda.',
    'why_choose_us_p2': 'Dengan sentuhan keahlian dari tim yang berpengalaman, serta pelayanan yang tulus, kami berkomitmen memberikan pengalaman terbaik agar Anda dapat menikmati hari pernikahan dengan penuh percaya diri dan kebahagiaan.',

    # Gallery Section
    'gallery_title': 'Wujudkan Momen Spesialmu Bersama Kami',
    'gallery_img_1': 'https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=500&q=80',
    'gallery_img_2': 'https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=500&q=80',
    'gallery_img_3': 'https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=500&q=80',
    'gallery_img_4': 'https://images.unsplash.com/photo-1519225421980-715cb0215aed?auto=format&fit=crop&w=500&q=80',
    'gallery_img_5': 'https://images.unsplash.com/photo-1523438885200-e635ba2c371e?auto=format&fit=crop&w=500&q=80',
    'gallery_caption_1': 'Dekorasi Pengantin Premium',
    'gallery_caption_2': 'Pelaminan Mewah',
    'gallery_caption_3': 'Tenda Resepsi & Pencahayaan',
    'gallery_caption_4': 'Setup Meja Jamuan Pernikahan',
    'gallery_caption_5': 'Aksesoris Jalur Pengantin',

    # Footer Contact
    'footer_description': 'Layanan tata rias pengantin profesional, penyewaan dekorasi pelaminan, tenda, dan paket pernikahan lengkap di Sleman, Yogyakarta & sekitarnya.',
    'footer_address': 'Sleman, Daerah Istimewa Yogyakarta',
    'footer_phone': '0812-3456-7890',
    'footer_email': 'info@griyarias-saraswati.com',
    'footer_hours': 'Senin - Minggu: 08.00 - 21.00 WIB',

    # Social Media Links
    'social_whatsapp': 'https://wa.me/6281234567890',
    'social_instagram': '#',
    'social_facebook': '#',
    'social_tiktok': '#',

    # Invoice / Receipt
    'invoice_company_name': 'Griya Rias Saraswati',
    'invoice_tagline': 'Beauty, Elegance, and Wedding Needs',
    'invoice_address': 'Sleman, Yogyakarta',
    'invoice_phone': '081234567890',
}

def seed_settings():
    app = create_app()
    with app.app_context():
        created = 0
        skipped = 0
        for key, value in DEFAULT_SETTINGS.items():
            existing = SiteSetting.query.filter_by(key=key).first()
            if not existing:
                setting = SiteSetting(key=key, value=value)
                db.session.add(setting)
                created += 1
                print(f'  [+] Created: {key}')
            else:
                skipped += 1
                print(f'  [=] Skipped (exists): {key}')
        
        db.session.commit()
        print(f'\nDone! Created: {created}, Skipped: {skipped}')

if __name__ == '__main__':
    seed_settings()
