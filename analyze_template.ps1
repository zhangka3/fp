# 脚本位于项目根目录，JSON 与脚本同级
$json = Get-Content (Join-Path $PSScriptRoot "template_blocks.json") -Encoding UTF8 | ConvertFrom-Json

Write-Host "=== API Response Summary ===" -ForegroundColor Cyan
Write-Host "code: $($json.code)"
Write-Host "msg: $($json.msg)"
Write-Host ""

$items = $json.data.items
Write-Host "=== All Blocks (total: $($items.Count)) ===" -ForegroundColor Cyan
Write-Host ""

# Group by block_type
$typeGroups = $items | Group-Object -Property block_type
Write-Host "=== Block Type Distribution ===" -ForegroundColor Cyan
foreach ($g in $typeGroups) {
    Write-Host "block_type=$($g.Name) : count=$($g.Count)"
}
Write-Host ""

# Find page block (block_type=1)
$pageBlock = $items | Where-Object { $_.block_type -eq 1 }
if ($pageBlock) {
    Write-Host "=== Page Block (block_type=1) ===" -ForegroundColor Cyan
    Write-Host "block_id: $($pageBlock.block_id)"
    Write-Host "page children count: $($pageBlock.children.Count)"
    Write-Host "page children IDs:"
    $i = 0
    foreach ($childId in $pageBlock.children) {
        $i++
        Write-Host "  [$i] $childId"
    }
    Write-Host ""
    
    Write-Host "=== Root Children Analysis ===" -ForegroundColor Cyan
    $totalRoot = $pageBlock.children.Count
    $pngPlaceholderCount = 0
    $gridCount = 0
    $imageCount = 0
    
    # Build a lookup of all blocks by block_id
    $blockLookup = @{}
    foreach ($item in $items) {
        $blockLookup[$item.block_id] = $item
    }
    
    $i = 0
    foreach ($childId in $pageBlock.children) {
        $i++
        $block = $blockLookup[$childId]
        if (-not $block) {
            Write-Host "[$i] block_id=$childId -- NOT FOUND in blocks list" -ForegroundColor Red
            continue
        }
        
        $bt = $block.block_type
        $childCount = if ($block.children) { $block.children.Count } else { 0 }
        
        # Extract text content
        $textContent = ""
        if ($block.text) {
            $textContent = $block.text.elements[0].text_run.content
        } elseif ($block.heading1) {
            $textContent = $block.heading1.elements[0].text_run.content
        } elseif ($block.heading2) {
            $textContent = $block.heading2.elements[0].text_run.content
        } elseif ($block.heading3) {
            $textContent = $block.heading3.elements[0].text_run.content
        } elseif ($block.heading4) {
            $textContent = $block.heading4.elements[0].text_run.content
        } elseif ($block.heading5) {
            $textContent = $block.heading5.elements[0].text_run.content
        } elseif ($block.heading6) {
            $textContent = $block.heading6.elements[0].text_run.content
        } elseif ($block.heading7) {
            $textContent = $block.heading7.elements[0].text_run.content
        } elseif ($block.heading8) {
            $textContent = $block.heading8.elements[0].text_run.content
        } elseif ($block.heading9) {
            $textContent = $block.heading9.elements[0].text_run.content
        } elseif ($block.code) {
            $textContent = $block.code.elements[0].text_run.content
        } elseif ($block.quote) {
            $textContent = $block.quote.elements[0].text_run.content
        } elseif ($block.bullet) {
            $textContent = $block.bullet.elements[0].text_run.content
        } elseif ($block.ordered) {
            $textContent = $block.ordered.elements[0].text_run.content
        } elseif ($block.todo) {
            $textContent = $block.todo.elements[0].text_run.content
        } elseif ($block.numberedListBlock) {
            $textContent = $block.numberedListBlock.elements[0].text_run.content
        }
        
        if ($textContent.Length -gt 80) {
            $textContent = $textContent.Substring(0, 80) + "..."
        }
        
        # Check if it's a PNG placeholder
        $isPngPlaceholder = $textContent -match "\[.*\.png\]"
        
        if ($isPngPlaceholder) { $pngPlaceholderCount++ }
        if ($bt -eq 24) { $gridCount++ }
        
        $btDesc = switch ($bt) {
            1 { "page" }
            2 { "text" }
            3 { "heading1" }
            4 { "heading2" }
            5 { "heading3" }
            6 { "heading4" }
            7 { "heading5" }
            8 { "heading6" }
            9 { "heading7" }
            10 { "heading8" }
            11 { "heading9" }
            12 { "bullet" }
            13 { "ordered" }
            14 { "code" }
            15 { "quote" }
            16 { "todo" }
            17 { "numberedListBlock" }
            18 { "bulletBlock" }
            19 { "orderedBlock" }
            20 { "divider" }
            21 { "calloutBlock" }
            22 { "chatCardBlock" }
            23 { "boardBlock" }
            24 { "grid" }
            25 { "gridColumn" }
            26 { "iframe" }
            27 { "image" }
            28 { "file" }
            29 { "media" }
            30 { "table" }
            31 { "tableCell" }
            32 { "view" }
            33 { "sheet" }
            34 { "jira" }
            35 { "bitable" }
            36 { "diagram" }
            37 { "flowchart" }
            38 { "mindnote" }
            39 { "doc" }
            40 { "grid2Column" }
            41 { "grid3Column" }
            42 { "grid4Column" }
            43 { "grid5Column" }
            44 { "embedPanel" }
            45 { "okr" }
            46 { "innerDoc" }
            47 { "link" }
            48 { "imageLink" }
            49 { "task" }
            50 { "taskList" }
            51 { "subTask" }
            52 { "whiteboard" }
            53 { "addOnBlock" }
            54 { "addOnBlockV2" }
            55 { "unknown" }
            default { "unknown($bt)" }
        }
        
        Write-Host "[$i] block_id=$($block.block_id) | type=$bt ($btDesc) | children=$childCount | png=$isPngPlaceholder"
        if ($textContent) {
            Write-Host "     text: $textContent"
        } else {
            Write-Host "     text: (empty)"
        }
        Write-Host ""
    }
    
    Write-Host "=== Summary ===" -ForegroundColor Cyan
    Write-Host "Total root children: $totalRoot"
    Write-Host "PNG placeholder text blocks: $pngPlaceholderCount"
    Write-Host "Grid blocks (type=24): $gridCount"
    
    # Also count image blocks in entire document (block_type=27)
    $allImages = $items | Where-Object { $_.block_type -eq 27 }
    $imageCount = $allImages.Count
    Write-Host "Image blocks (type=27) in entire document: $imageCount"
    
    Write-Host ""
    Write-Host "=== Grid Children ===" -ForegroundColor Cyan
    foreach ($childId in $pageBlock.children) {
        $block = $blockLookup[$childId]
        if ($block.block_type -eq 24) {
            Write-Host "Grid block_id=$($block.block_id) has children:"
            $j = 0
            if ($block.children) {
                foreach ($gChildId in $block.children) {
                    $j++
                    $gChild = $blockLookup[$gChildId]
                    if ($gChild) {
                        $gBt = $gChild.block_type
                        $gBtDesc = switch ($gBt) {
                            25 { "gridColumn" }
                            27 { "image" }
                            default { "other($gBt)" }
                        }
                        Write-Host "  [$j] block_id=$gChildId | type=$gBt ($gBtDesc) | children=$($gChild.children.Count)"
                    } else {
                        Write-Host "  [$j] block_id=$gChildId | NOT FOUND"
                    }
                }
            }
            Write-Host ""
        }
    }
    
} else {
    Write-Host "No page block found!" -ForegroundColor Red
}
