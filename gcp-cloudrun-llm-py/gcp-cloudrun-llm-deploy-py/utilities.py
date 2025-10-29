def service_name_shortener(name):
    max_length = 50  # Cloud Run service name max length is 50 chars
    if len(name) <= max_length:
        return name
    truncated_name = name[:max_length]
    # Check if the last character is undesirable and adjust if needed
    while truncated_name and not truncated_name[-1].isalnum():
        truncated_name = truncated_name[:-1]
    return truncated_name