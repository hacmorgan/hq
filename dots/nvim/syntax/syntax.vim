" Language   : Help Page
" Maintainer : Zdzislaw Sliwinski
" Last change: 9 Oct 2020

if exists("b:current_syntax")
 finish
endif

syn match hpLongOption '\v--(\w|-)+'
syn match hpShortOption '\v\W-\w\W'
syn match hpValue '<[^>]\+>'
syn match hpFlag '\v\w+(-\w+)?(\[\d\])?(,\w+(-\w+)?(\[\d\])?)*[ ]*:'
syn match hpVariable '\v\w+\=.{-}[;:]' contains=hpValue

hi def link hpLongOption String
hi def link hpShortOption String
hi def link hpValue Type
hi def link hpFlag Identifier
hi def link hpVariable Identifier

" vim: ts=4
