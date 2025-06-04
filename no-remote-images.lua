-- no-remote-images.lua
function Image (el)
  -- Check if the image source starts with http:// or https://
  if el.src:match("^https?://") then
    -- Replace the remote image with a placeholder string indicating its original source
    return pandoc.Str("[Remote Image Removed: " .. el.src .. "]")
  end
  -- If it's not a remote image (e.g., a local file path), return it unchanged
  return el
end