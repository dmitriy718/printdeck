#!/usr/bin/env python3
"""Repository-level safety and release invariants for the controller."""

from __future__ import annotations

import csv
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def production_text() -> str:
    paths = [
        *ROOT.glob("components/**/*.[ch]"),
        *ROOT.glob("main/**/*.[ch]"),
        ROOT / "CMakeLists.txt",
        ROOT / "main/idf_component.yml",
        ROOT / "partitions.csv",
        ROOT / "sdkconfig.defaults",
    ]
    return "\n".join(
        path.read_text(encoding="utf-8") for path in paths if path.is_file()
    )


class ReleaseInvariants(unittest.TestCase):
    def test_release_version_is_current(self) -> None:
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn('set(PROJECT_VER "0.7.2")', cmake)

    def test_public_product_identity_is_printdeck(self) -> None:
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        ui = (ROOT / "components/nh_ui/src/nh_ui.c").read_text(
            encoding="utf-8"
        )
        ota = (ROOT / "components/nh_ota/src/nh_ota.c").read_text(
            encoding="utf-8"
        )
        printer = (ROOT / "components/nh_printer/src/nh_printer.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("project(printdeck)", cmake)
        self.assertIn('"PRINTDECK"', ui)
        self.assertNotIn('"NOVA HORIZON"', ui)
        self.assertIn(r'\"service\":\"printdeck-ota\"', ota)
        self.assertIn('"printdeck-%s"', printer)

    def test_ota_uploader_supports_identity_migration(self) -> None:
        uploader = (ROOT / "scripts/ota-update.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("build/printdeck.bin", uploader)
        self.assertIn('{"printdeck-ota", "nova-horizon-ota"}', uploader)
        self.assertIn(
            'data.get("service") != "printdeck-ota" '
            'or data.get("version") != expected',
            uploader,
        )

    def test_no_development_device_defaults_are_compiled(self) -> None:
        text = production_text()
        private_ipv4 = re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"192\.168\.\d{1,3}\.\d{1,3}|"
            r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
        )
        self.assertIsNone(private_ipv4.search(text))
        self.assertNotIn("01P00C630601209", text)
        app = (ROOT / "main/app_main.c").read_text(encoding="utf-8")
        self.assertIn(".default_ip = NULL", app)
        self.assertIn(".default_serial = NULL", app)

    def test_bambu_ca_has_one_source_of_truth(self) -> None:
        component_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in ROOT.glob("components/**/*.[ch]")
        )
        self.assertEqual(component_text.count("-----BEGIN CERTIFICATE-----"), 1)
        self.assertIn("nh_bambu_ca_pem", component_text)

    def test_wifi_remote_dependency_is_bounded(self) -> None:
        manifest = (ROOT / "main/idf_component.yml").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            manifest,
            r'espressif/esp_wifi_remote:\s*\n\s*version:\s*"1\.6\.3"',
        )
        self.assertNotRegex(
            manifest,
            r'espressif/esp_wifi_remote:\s*\n\s*version:\s*"\*"',
        )

    def test_sd_mount_cannot_format_media(self) -> None:
        board = (ROOT / "components/nh_board/src/nh_board.c").read_text(
            encoding="utf-8"
        )
        self.assertIn(".format_if_mount_failed = false", board)
        self.assertIn("sdmmc_get_status(s_sd_card)", board)
        self.assertIn("esp_vfs_fat_sdmmc_mount(", board)
        self.assertNotIn("esp_vfs_fat_sdspi_mount(", board)
        self.assertIn("host.init = use_hosted_sdmmc_controller", board)
        self.assertIn("host.slot = SDMMC_HOST_SLOT_0", board)
        self.assertIn("NH_SD_CLK_GPIO = GPIO_NUM_43", board)
        self.assertIn("NH_SD_CMD_GPIO = GPIO_NUM_44", board)
        self.assertIn("NH_SD_D0_GPIO = GPIO_NUM_39", board)
        self.assertIn("NH_SD_D1_GPIO = GPIO_NUM_40", board)
        self.assertIn("NH_SD_D2_GPIO = GPIO_NUM_41", board)
        self.assertIn("NH_SD_D3_GPIO = GPIO_NUM_42", board)

    def test_sd_mount_runs_after_hosted_network_init(self) -> None:
        main = (ROOT / "main" / "app_main.c").read_text(encoding="utf-8")
        self.assertLess(
            main.index("nh_network_init(&network_cfg)"),
            main.index("refresh_controller_sd();", main.index("void app_main")),
        )

    def test_boya_flash_driver_is_enabled_for_the_prototype(self) -> None:
        defaults = (ROOT / "sdkconfig.defaults").read_text(encoding="utf-8")
        self.assertIn("CONFIG_SPI_FLASH_SUPPORT_BOYA_CHIP=y", defaults)

    def test_ota_disconnect_reports_returned_device_state(self) -> None:
        uploader = (ROOT / "scripts" / "ota-update.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("diagnose_upload_disconnect", uploader)
        self.assertIn('data.get("reset_reason", "unknown")', uploader)
        self.assertIn('data.get("partition", "unknown")', uploader)
        self.assertIn("Do not retry", uploader)

    def test_time_sync_starts_only_after_network_address(self) -> None:
        network = (ROOT / "components/nh_network/src/nh_network.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("time_config.start = false", network)
        self.assertIn("esp_netif_sntp_start()", network)

    def test_header_clock_uses_twelve_hour_time(self) -> None:
        ui = (ROOT / "components/nh_ui/src/nh_ui.c").read_text(
            encoding="utf-8"
        )
        self.assertIn('local_time.tm_hour < 12 ? "AM" : "PM"', ui)
        self.assertNotIn('"%H:%M"', ui)

    def test_files_page_does_not_present_future_sources_as_files(self) -> None:
        ui = (ROOT / "components/nh_ui/src/nh_ui.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("NO INDEXED .3MF FILES", ui)
        self.assertNotIn("Nova cloud queue", ui)
        self.assertNotIn("USB / network import", ui)

    def test_control_lock_reason_tracks_print_state(self) -> None:
        ui = (ROOT / "components/nh_ui/src/nh_ui.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("Locked during active print", ui)
        self.assertIn("Motion controls disabled", ui)
        self.assertNotIn("Hardware validation pending", ui)

    def test_wifi_ui_accepts_raw_64_character_psk(self) -> None:
        ui = (ROOT / "components/nh_ui/src/nh_ui.c").read_text(
            encoding="utf-8"
        )
        network = (ROOT / "components/nh_network/src/nh_network.c").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "lv_textarea_set_max_length(s_ui.network_password, 64)", ui
        )
        self.assertIn(
            "memcpy(station.sta.password, s_pending_password, password_length)",
            network,
        )
        self.assertIn(
            "memcpy(station.sta.ssid, s_pending_ssid, ssid_length)", network
        )

    def test_failed_wifi_replacement_has_a_rollback_path(self) -> None:
        network = (ROOT / "components/nh_network/src/nh_network.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("preserve_saved_credentials()", network)
        self.assertIn("clear_backup_credentials()", network)
        self.assertIn("restoring saved network", network)
        self.assertIn("valid_credentials(s_pending_ssid, s_pending_password)", network)

    def test_unsynchronized_clock_cannot_reject_printer_profile(self) -> None:
        printer = (ROOT / "components/nh_printer/src/nh_printer.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("system_clock_ready()", printer)
        self.assertIn("waiting for network time synchronization", printer)

    def test_camera_waits_for_persisted_current_printer_profile(self) -> None:
        printer_header = (
            ROOT / "components/nh_printer/include/nh_printer.h"
        ).read_text(encoding="utf-8")
        ui = (ROOT / "components/nh_ui/src/nh_ui.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("bool profile_ready;", printer_header)
        self.assertIn("camera_profile_ready()", ui)
        self.assertIn("!s_ui.camera_requested_active", ui)

    def test_printer_ui_updates_publish_a_locked_deep_copy(self) -> None:
        printer = (ROOT / "components/nh_printer/src/nh_printer.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("xSemaphoreCreateMutex()", printer)
        self.assertIn("snapshot_copy = *s_snapshot", printer)
        self.assertIn("status_copy = s_status", printer)
        self.assertIn(
            "s_config.update_cb(&snapshot_copy, &status_copy", printer
        )

    def test_partition_table_fits_flash_without_overlap(self) -> None:
        partitions: list[tuple[str, int, int]] = []
        with (ROOT / "partitions.csv").open(
            encoding="utf-8", newline=""
        ) as stream:
            rows = csv.reader(
                line for line in stream if not line.lstrip().startswith("#")
            )
            for row in rows:
                if not row:
                    continue
                name = row[0].strip()
                offset = int(row[3].strip(), 0)
                size = int(row[4].strip(), 0)
                partitions.append((name, offset, offset + size))

        self.assertTrue(partitions)
        partitions.sort(key=lambda item: item[1])
        for previous, current in zip(partitions, partitions[1:]):
            self.assertLessEqual(
                previous[2],
                current[1],
                f"{previous[0]} overlaps {current[0]}",
            )
        self.assertLessEqual(partitions[-1][2], 16 * 1024 * 1024)
        by_name = {
            name: end - offset for name, offset, end in partitions
        }
        self.assertGreaterEqual(by_name.get("coredump", 0), 512 * 1024)

    def test_coredump_task_limit_matches_reserved_partition(self) -> None:
        defaults = (ROOT / "sdkconfig.defaults").read_text(encoding="utf-8")
        self.assertIn("CONFIG_ESP_COREDUMP_MAX_TASKS_NUM=16", defaults)

    def test_ui_does_not_embed_a_stale_firmware_version(self) -> None:
        ui = (ROOT / "components/nh_ui/src/nh_ui.c").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(ui, r"FIRMWARE\s+v?\d+\.\d+\.\d+")
        self.assertIn("esp_app_get_description()", ui)

    def test_fresh_config_disables_every_unused_lvgl_feature(self) -> None:
        defaults = (ROOT / "sdkconfig.defaults").read_text(encoding="utf-8")
        disabled = {
            "ANIMIMG",
            "ARCLABEL",
            "CALENDAR",
            "CANVAS",
            "CHART",
            "CHECKBOX",
            "DROPDOWN",
            "IMAGEBUTTON",
            "KEYBOARD",
            "LED",
            "LINE",
            "LIST",
            "MENU",
            "MSGBOX",
            "ROLLER",
            "SCALE",
            "SPAN",
            "SPINBOX",
            "SPINNER",
            "SWITCH",
            "TABLE",
            "TABVIEW",
            "TILEVIEW",
            "WIN",
            "FLEX",
            "GRID",
            "OBSERVER",
            "THEME_SIMPLE",
        }
        for feature in disabled:
            self.assertIn(
                f"CONFIG_LV_USE_{feature}=n",
                defaults,
                f"fresh builds must disable unused LVGL {feature}",
            )

    def test_ota_requires_explicit_local_authorization(self) -> None:
        ota = (ROOT / "components/nh_ota/src/nh_ota.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("claim_update_window()", ota)
        self.assertIn('"403 Forbidden"', ota)
        self.assertIn("NH_OTA_MAX_CONSECUTIVE_TIMEOUTS", ota)

    def test_ota_images_are_signed_without_burning_secure_boot_fuses(self) -> None:
        defaults = (ROOT / "sdkconfig.defaults").read_text(encoding="utf-8")
        self.assertIn("CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT=y", defaults)
        self.assertIn("CONFIG_SECURE_SIGNED_APPS_RSA_SCHEME=y", defaults)
        self.assertIn(
            "CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y", defaults
        )
        self.assertIn("CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=y", defaults)
        self.assertNotIn("\nCONFIG_SECURE_BOOT=y", defaults)
        self.assertNotIn("\nCONFIG_SECURE_FLASH_ENC_ENABLED=y", defaults)

    def test_private_signing_material_is_ignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("security/private/", ignore)
        tracked = {
            line.strip()
            for line in subprocess.check_output(
                ["git", "ls-files"], cwd=ROOT, text=True
            ).splitlines()
        }
        tracked_private = [
            path for path in ROOT.glob("security/private/**/*") if path.is_file()
        ]
        self.assertFalse(
            any(
                str(path.relative_to(ROOT)) in tracked
                for path in tracked_private
            )
        )
        ota_script = (ROOT / "scripts/ota-update.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("ESP Secure Boot v2 public-key digest:", ota_script)
        self.assertIn("actual_digest", ota_script)
        self.assertIn("Refusing firmware signed by an unexpected key", ota_script)

    def test_timezone_is_persistent_and_not_hardcoded_in_ui(self) -> None:
        ui = (ROOT / "components/nh_ui/src/nh_ui.c").read_text(
            encoding="utf-8"
        )
        settings = (
            ROOT / "components/nh_settings/src/nh_settings.c"
        ).read_text(encoding="utf-8")
        self.assertNotIn('setenv("TZ"', ui)
        self.assertIn('nvs_set_u8(s_nvs, NVS_TIMEZONE_KEY', settings)
        self.assertIn("nh_settings_timezone_next", settings)

    def test_runtime_health_avoids_trace_facility(self) -> None:
        defaults = (ROOT / "sdkconfig.defaults").read_text(encoding="utf-8")
        diagnostics = (
            ROOT / "components/nh_diagnostics/src/nh_diagnostics.c"
        ).read_text(encoding="utf-8")
        ota = (ROOT / "components/nh_ota/src/nh_ota.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("CONFIG_FREERTOS_USE_TRACE_FACILITY=n", defaults)
        self.assertIn("uxTaskGetStackHighWaterMark", diagnostics)
        self.assertIn("ESP_PARTITION_SUBTYPE_DATA_COREDUMP", diagnostics)
        self.assertIn(r'\"minimum_free\"', ota)
        self.assertIn(r'\"coredump\"', ota)


if __name__ == "__main__":
    unittest.main(verbosity=2)
