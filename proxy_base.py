import google_crc32c


def construct_url(base_url: str, url: str) -> str:
    return (
        f"{base_url}/{url}"
        if base_url[-1] != "/"
        else f"{base_url[:-2]}/{url}"
    )


def check_crc(arg0):
    # Verify payload checksum.
    crc32 = google_crc32c.Checksum()
    crc32.update(arg0.payload.data)
    assert arg0.payload.data_crc32c == int(
        crc32.hexdigest(), 16
    ), "data corruption"
