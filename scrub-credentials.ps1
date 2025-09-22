# PowerShell script to scrub credentials from git commit messages
$input | 
    ForEach-Object { 
        $_ -replace 'udohpeterbrown@gmail.com', '{{REDACTED_EMAIL}}' 
    } |
    ForEach-Object { 
        $_ -replace 'fdac hcuq libc ctsb', '{{REDACTED_PASSWORD}}' 
    }