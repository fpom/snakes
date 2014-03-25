var nodeColor;

function abcdon () {
  obj = $(this);
  if (obj.attr("class") == "node") {
    node = obj.children().children().first();
    nodeColor = node.attr("fill");
    node.attr("fill", "yellow");
  } else {
    obj.addClass("highlight");
  }
  $(obj.attr("data-abcd")).addClass("highlight");
};

function abcdoff () {
  obj = $(this);
  if (obj.attr("class") == "node") {
    node = obj.children().children().first();
    node.attr("fill", nodeColor);
  } else {
    obj.removeClass("highlight");
  }
  $(obj.attr("data-abcd")).removeClass("highlight");
};

function treeon () {
  obj = $(this);
  if (obj.attr("class") != "node") {
    obj.addClass("highlight");
  }
  $(obj.attr("data-tree")).addClass("highlight");
};

function treeoff () {
  obj = $(this);
  if (obj.attr("class") != "node") {
    obj.removeClass("highlight");
  }
  $(obj.attr("data-tree")).removeClass("highlight");
};

function neton () {
  obj = $(this);
  $(obj.attr("data-net")).each(function () {
      node = $(this).children().children().first();
      nodeColor = node.attr("fill");
      node.attr("fill", "yellow");
  });
  obj.addClass("highlight");
};

function netoff () {
  obj = $(this);
  $(obj.attr("data-net")).each(function () {
      node = $(this).children().children().first();
      node.attr("fill", nodeColor);
  });
  obj.removeClass("highlight");
};

$(document).ready(function() {
    $("#model [data-abcd]").hover(abcdon, abcdoff);
    $("#model [data-tree]").hover(treeon, treeoff);
    $("#model [data-net]").hover(neton, netoff);
    $(".tree .instance, .tree .action").each(function () {
        obj = $(this);
        obj.html($(obj.attr("data-abcd")).html());
    });
});
