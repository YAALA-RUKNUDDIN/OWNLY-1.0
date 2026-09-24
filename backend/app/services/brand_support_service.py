"""Curated brand support directory for warranty claims and customer service."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BrandSupportInfo:
    brand: str
    category: str
    support_phone: str
    support_url: str
    claim_portal_url: str
    warranty_check_url: Optional[str] = None
    serial_lookup_url: Optional[str] = None
    support_hours: str = "Mon-Fri 9am-6pm local time"
    notes: Optional[str] = None


BRAND_DIRECTORY: dict[str, BrandSupportInfo] = {
    "apple": BrandSupportInfo(
        brand="Apple",
        category="Electronics & Computers",
        support_phone="1-800-275-2273",
        support_url="https://support.apple.com",
        claim_portal_url="https://getsupport.apple.com",
        warranty_check_url="https://checkcoverage.apple.com",
        serial_lookup_url="https://checkcoverage.apple.com",
        support_hours="24/7 Phone & Chat Support",
        notes="AppleCare covers hardware repairs and phone support.",
    ),
    "samsung": BrandSupportInfo(
        brand="Samsung",
        category="Electronics & Appliances",
        support_phone="1-800-726-7864",
        support_url="https://www.samsung.com/us/support/",
        claim_portal_url="https://www.samsung.com/us/support/service/request/",
        warranty_check_url="https://www.samsung.com/us/support/warranty/",
        support_hours="24/7 Support via Call & SMS",
        notes="Requires serial number/IMEI and original proof of purchase.",
    ),
    "sony": BrandSupportInfo(
        brand="Sony",
        category="Audio & Electronics",
        support_phone="1-800-222-7669",
        support_url="https://us.esm.sony.com/support",
        claim_portal_url="https://us.esm.sony.com/support/repair",
        warranty_check_url="https://productregistration.sony.com",
        support_hours="Mon-Fri 9am-8pm EST",
    ),
    "dell": BrandSupportInfo(
        brand="Dell",
        category="Computers",
        support_phone="1-800-624-9896",
        support_url="https://www.dell.com/support",
        claim_portal_url="https://www.dell.com/support/home/en-us/servicecenter",
        warranty_check_url="https://www.dell.com/support/home/en-us?app=warranty",
        serial_lookup_url="https://www.dell.com/support/home/en-us",
        support_hours="24/7 Technical Support for in-warranty systems",
        notes="Locate your 7-character Dell Service Tag before contacting.",
    ),
    "hp": BrandSupportInfo(
        brand="HP",
        category="Computers & Printers",
        support_phone="1-800-474-6836",
        support_url="https://support.hp.com",
        claim_portal_url="https://support.hp.com/us-en/service-center",
        warranty_check_url="https://support.hp.com/us-en/checkwarranty",
        support_hours="24/7 Virtual Agent, Phone Mon-Fri 8am-8pm EST",
    ),
    "lenovo": BrandSupportInfo(
        brand="Lenovo",
        category="Computers & Tablets",
        support_phone="1-855-253-6686",
        support_url="https://support.lenovo.com",
        claim_portal_url="https://support.lenovo.com/us/en/servicerequest",
        warranty_check_url="https://pcsupport.lenovo.com/us/en/warrantylookup",
        support_hours="Mon-Fri 9am-9pm EST",
    ),
    "lg": BrandSupportInfo(
        brand="LG",
        category="Appliances & Displays",
        support_phone="1-800-243-0000",
        support_url="https://www.lg.com/us/support",
        claim_portal_url="https://www.lg.com/us/support/repair-service/schedule-repair",
        warranty_check_url="https://www.lg.com/us/support/warranty-information",
        support_hours="Daily 8am-9pm EST",
    ),
    "bose": BrandSupportInfo(
        brand="Bose",
        category="Audio",
        support_phone="1-800-379-2073",
        support_url="https://support.bose.com",
        claim_portal_url="https://support.bose.com/s/service-and-repair",
        support_hours="Mon-Fri 9am-8pm EST, Sat 9am-6pm EST",
    ),
    "dyson": BrandSupportInfo(
        brand="Dyson",
        category="Appliances & Personal Care",
        support_phone="1-866-693-9766",
        support_url="https://www.dyson.com/support",
        claim_portal_url="https://www.dyson.com/support/journey/repairs",
        warranty_check_url="https://www.dyson.com/registration",
        support_hours="Mon-Fri 8am-8pm CST, Sat 9am-6pm CST",
    ),
    "microsoft": BrandSupportInfo(
        brand="Microsoft",
        category="Computers & Gaming",
        support_phone="1-800-642-7676",
        support_url="https://support.microsoft.com",
        claim_portal_url="https://support.microsoft.com/devices",
        warranty_check_url="https://account.microsoft.com/devices",
        support_hours="24/7 Digital Support & Scheduling",
        notes="Sign in with your Microsoft account to register Surface or Xbox hardware.",
    ),
    "google": BrandSupportInfo(
        brand="Google",
        category="Electronics & Mobile",
        support_phone="1-855-836-3987",
        support_url="https://support.google.com/pixelphone",
        claim_portal_url="https://store.google.com/repair",
        warranty_check_url="https://store.google.com/repair",
        support_hours="24/7 Chat & Phone Support",
    ),
    "nintendo": BrandSupportInfo(
        brand="Nintendo",
        category="Gaming",
        support_phone="1-800-255-3700",
        support_url="https://en-americas-support.nintendo.com",
        claim_portal_url="https://repair.nintendo.com",
        support_hours="Daily 6am-7pm PST",
    ),
    "asus": BrandSupportInfo(
        brand="ASUS",
        category="Computers & Components",
        support_phone="1-888-678-3688",
        support_url="https://www.asus.com/us/support/",
        claim_portal_url="https://www.asus.com/us/support/article/818/",
        warranty_check_url="https://www.asus.com/us/support/warranty-status-inquiry/",
        support_hours="Mon-Fri 6am-9pm PST, Sat-Sun 6am-5pm PST",
    ),
    "whirlpool": BrandSupportInfo(
        brand="Whirlpool",
        category="Appliances",
        support_phone="1-866-698-2538",
        support_url="https://www.whirlpool.com/services/contact-us.html",
        claim_portal_url="https://www.whirlpool.com/owners.html",
        support_hours="Mon-Fri 8am-6pm EST",
    ),
    "kitchenaid": BrandSupportInfo(
        brand="KitchenAid",
        category="Kitchen Appliances",
        support_phone="1-800-541-6390",
        support_url="https://www.kitchenaid.com/resources.html",
        claim_portal_url="https://www.kitchenaid.com/owners.html",
        support_hours="Mon-Fri 8am-6pm EST",
    ),
    "canon": BrandSupportInfo(
        brand="Canon",
        category="Cameras & Printers",
        support_phone="1-800-652-2666",
        support_url="https://www.usa.canon.com/support",
        claim_portal_url="https://www.usa.canon.com/support/service-and-repair",
        support_hours="Mon-Fri 8am-8pm EST",
    ),
    "logitech": BrandSupportInfo(
        brand="Logitech",
        category="Peripherals",
        support_phone="1-646-454-3200",
        support_url="https://support.logi.com",
        claim_portal_url="https://support.logi.com/hc/en-us/requests/new?ticket_form_id=360000621393",
        support_hours="Mon-Fri 9am-9pm EST",
    ),
}


class BrandSupportService:
    @staticmethod
    def get_brand_support(brand_name: Optional[str]) -> Optional[BrandSupportInfo]:
        """Look up curated brand support information by name with fuzzy prefix matching."""
        if not brand_name:
            return None
        key = brand_name.strip().lower()
        if key in BRAND_DIRECTORY:
            return BRAND_DIRECTORY[key]
        for brand_key, info in BRAND_DIRECTORY.items():
            if brand_key in key or key in brand_key:
                return info
        return None

    @staticmethod
    def list_all_brands(category: Optional[str] = None) -> list[BrandSupportInfo]:
        """List all supported brands, optionally filtered by category."""
        results = list(BRAND_DIRECTORY.values())
        if category:
            cat_lower = category.strip().lower()
            results = [b for b in results if cat_lower in b.category.lower()]
        return sorted(results, key=lambda b: b.brand)
