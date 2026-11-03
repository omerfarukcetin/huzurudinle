# ehlisunnetbuyukleri.com sesli kitap listesinden tum kitaplari ve MP3 linklerini toplar -> books.json
$ua   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0"
$base = "https://www.ehlisunnetbuyukleri.com"

$index = Invoke-WebRequest -UseBasicParsing -Uri "$base/Hakikat-Kitabevi/Dinle" -UserAgent $ua
$detayLinks = [regex]::Matches($index.Content, 'href="(/Hakikat-Kitabevi/Dinle/Detay/[^"]*)"') |
    ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique

$books = foreach ($path in $detayLinks) {
    $page = Invoke-WebRequest -UseBasicParsing -Uri ($base + $path) -UserAgent $ua

    # Kitap adi: URL'deki slug'dan
    $slug  = [uri]::UnescapeDataString(($path -split '/')[4])
    $title = ($slug -replace '-', ' ').Trim()

    # Sayfadaki Türkçe karakterli bölüm adları ("05 İmanın Şartları") — MP3 linkiyle eşleştir
    $titles = @{}
    [regex]::Matches($page.Content, '(?s)Kitaplar_Dinle_List_text">\s*(.*?)\s*</div>.*?(/Documents/kitaplar_sesli/[^"''\s<>]+?\.mp3)') |
        ForEach-Object {
            $t = [System.Net.WebUtility]::HtmlDecode($_.Groups[1].Value) -replace '\s+', ' '
            if (-not $titles.ContainsKey($_.Groups[2].Value)) { $titles[$_.Groups[2].Value] = ($t -replace '^\d+\s*[-.]?\s*', '').Trim() }
        }

    $tracks = [regex]::Matches($page.Content, '/Documents/kitaplar_sesli/[^"''\s<>]+?\.mp3') |
        ForEach-Object { $_.Value } | Select-Object -Unique |
        ForEach-Object {
            $file = [uri]::UnescapeDataString(($_ -split '/')[-1])
            $name = $titles[$_]
            if (-not $name) { $name = (($file -replace '\.mp3$', '') -replace '^\d+_', '' -replace '_', ' ').Trim() }
            # Mektûbât: 313 sesli dosya 1. cildin 313 mektubudur; kaynakta hepsinin adı yalnızca "Mektub"
            if ($_ -like '*/Mektubat_Tercemesi/*') {
                if ($name -eq 'Mektub' -and $file -match '^(\d+)_') { $name = "1. Cild, $([int]$Matches[1]). Mektub" }
                $name = $name -creplace '^[A-E] (?=\p{Lu})', ''   # "A Ön Kapak İçi" → "Ön Kapak İçi" (sıralama harfi)
            }
            [ordered]@{ name = $name; url = $base + $_ }
        }

    Write-Host ("{0,-45} {1,4} bolum" -f $title, @($tracks).Count)
    [ordered]@{ title = $title; source = $base + $path; tracks = @($tracks) }
}

$json = ConvertTo-Json -InputObject @($books) -Depth 5
$utf8 = New-Object Text.UTF8Encoding $false
[IO.File]::WriteAllText((Join-Path $PSScriptRoot "books.json"), $json, $utf8)
# index.html bunu <script> ile yukler; boylece sunucusuz (cift tiklayarak) da calisir
[IO.File]::WriteAllText((Join-Path $PSScriptRoot "books.js"), "window.BOOKS = $json;", $utf8)
Write-Host "books.json ve books.js yazildi."
